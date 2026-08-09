"""
The ensemble/aggregation mechanism — FORECAST_ENGINE_SPEC.md, Section 6.

Two combination methods: `simple_average_ensemble` and
`inverse_error_weighted_ensemble`. Both:

- require every input forecast to share a single `subject`
  (an ensemble across different questions is meaningless);
- require every input forecast to already share a single, non-null
  `disagreement_set_ref` — this function does not invent a grouping,
  consistent with FORECAST_ENGINE_SPEC.md Section 6's framing that the
  ensemble is an *additional* UAP alongside the individual model outputs,
  not a replacement, and grouping decisions happen upstream;
- tag the returned ensemble UAP's `dependencies` with every input's `id`,
  and its `disagreement_set_ref` with the shared value already present on
  the inputs — these two fields serve distinct purposes and are never
  conflated: `dependencies` records provenance (what this was computed
  from), `disagreement_set_ref` records grouping (what else answers the
  same question);
- never mutate the input UAPs;
- derive `confidence` from the spread of the input results, per Section
  6's requirement that "low agreement between constituent models should
  widen the ensemble's uncertainty bounds, not narrow them" — see
  `_confidence_from_spread` below for the (documented, heuristic)
  thresholds used.

Neither function implements, chooses, or stubs any forecasting model —
inputs are supplied UAPs, exactly as FORECAST_ENGINE_SPEC.md Section 5
leaves model choice undecided.
"""

from __future__ import annotations

import statistics

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

# Guard against a zero or near-zero historical_error, mirroring
# quant-engine's Sharpe-ratio zero-denominator guard: a zero error implies
# infinite weight, which is not a meaningful result. Errors are also
# required to be strictly positive (an error magnitude), so this same
# threshold check catches negative values too.
_ERROR_EPSILON = 1e-9

# Confidence-from-spread heuristic thresholds. FORECAST_ENGINE_SPEC.md
# Section 6 requires that low agreement widen uncertainty, but specifies
# no thresholds — this cut-point on the *relative* spread (population
# stdev of inputs, divided by the scale of their mean) is a reasonable,
# documented heuristic chosen here, not a value fixed anywhere in the
# specification.
_RELATIVE_SPREAD_MODERATE_CONFIDENCE_MAX = 0.30
_SCALE_EPSILON = 1e-9


def _confidence_from_spread(values: list[float]) -> ConfidenceLevel:
    """
    Map the relative spread of `values` to a ConfidenceLevel: low or
    moderate spread -> MODERATE, high spread -> LOW.

    Never returns HIGH, even for perfectly clustered inputs (spread ~0):
    both callers below construct an ensemble UAP with validation_status
    hardcoded PROVISIONAL, and UAP's own model-level guardrail
    (shared/optifi_shared/uap.py) requires HIGH confidence to pair with a
    settled status (VERIFIED/SUPERSEDED). Internal agreement among the
    input models is not the same thing as external corroboration, so it
    should never by itself justify claiming HIGH confidence on an
    uncorroborated estimate — MODERATE is the ceiling here regardless of
    how tightly the inputs agree.
    """
    if len(values) == 1:
        return ConfidenceLevel.MODERATE  # no disagreement possible, but still uncorroborated

    mean_val = statistics.mean(values)
    stdev_val = statistics.pstdev(values)
    scale = max(abs(mean_val), _SCALE_EPSILON)
    relative_spread = stdev_val / scale

    if relative_spread <= _RELATIVE_SPREAD_MODERATE_CONFIDENCE_MAX:
        return ConfidenceLevel.MODERATE
    else:
        return ConfidenceLevel.LOW


def _validate_shared_subject_and_disagreement_ref(
    forecasts: list[UAP], fn_name: str
) -> tuple[str, str]:
    if not forecasts:
        raise ValueError(f"{fn_name}: `forecasts` must be a non-empty list.")

    subjects = {f.subject for f in forecasts}
    if len(subjects) != 1:
        raise ValueError(
            f"{fn_name}: all input forecasts must share the same `subject` "
            f"— an ensemble across different questions is meaningless; "
            f"got {sorted(subjects)}."
        )

    disagreement_refs = {f.disagreement_set_ref for f in forecasts}
    if len(disagreement_refs) != 1 or None in disagreement_refs:
        raise ValueError(
            f"{fn_name}: all input forecasts must already share a single, "
            "non-null `disagreement_set_ref` — grouping decisions happen "
            "upstream of this function, which does not invent one."
        )

    return forecasts[0].subject, forecasts[0].disagreement_set_ref


def simple_average_ensemble(forecasts: list[UAP]) -> UAP:
    """
    Simple-average ensemble (FORECAST_ENGINE_SPEC.md, Section 6):
    forecast_ensemble = (1/n) * sum(f_i).
    """
    subject, disagreement_set_ref = _validate_shared_subject_and_disagreement_ref(
        forecasts, "simple_average_ensemble"
    )

    values = [f.result for f in forecasts]
    ensemble_result = sum(values) / len(values)

    return UAP(
        subject=subject,
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=ensemble_result,
        source="computed as a simple average of the provided forecast UAPs",
        producer="forecast-engine / simple-average ensemble, FORECAST_ENGINE_SPEC.md Section 6",
        confidence=_confidence_from_spread(values),
        assumptions=[
            "each input forecast is expressed on the same scale and "
            "answers the same question",
        ],
        limitations=[
            "a simple average weights every input equally regardless of "
            "each model's historical accuracy",
        ],
        dependencies=[f.id for f in forecasts],
        disagreement_set_ref=disagreement_set_ref,
    )


def inverse_error_weighted_ensemble(
    forecasts: list[UAP], historical_errors: list[float]
) -> UAP:
    """
    Inverse-error-weighted ensemble (FORECAST_ENGINE_SPEC.md, Section 6):
    w_i = (1/error_i) / sum(1/error_j), then
    forecast_ensemble = sum(w_i * f_i).
    """
    if len(forecasts) != len(historical_errors):
        raise ValueError(
            "inverse_error_weighted_ensemble: `forecasts` and "
            f"`historical_errors` must be the same length "
            f"({len(forecasts)} vs {len(historical_errors)})."
        )
    for i, error in enumerate(historical_errors):
        if error < _ERROR_EPSILON:
            raise ValueError(
                f"inverse_error_weighted_ensemble: historical_errors[{i}] "
                f"({error!r}) is zero, negative, or below the epsilon "
                f"threshold ({_ERROR_EPSILON}); a zero or negative error "
                "implies an infinite or nonsensical weight, which is not "
                "a meaningful result."
            )

    subject, disagreement_set_ref = _validate_shared_subject_and_disagreement_ref(
        forecasts, "inverse_error_weighted_ensemble"
    )

    inverse_errors = [1 / error for error in historical_errors]
    total_inverse_error = sum(inverse_errors)
    weights = [inverse_error / total_inverse_error for inverse_error in inverse_errors]

    values = [f.result for f in forecasts]
    ensemble_result = sum(w * v for w, v in zip(weights, values))

    return UAP(
        subject=subject,
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=ensemble_result,
        source="computed as an inverse-error-weighted average of the provided forecast UAPs",
        producer="forecast-engine / inverse-error-weighted ensemble, FORECAST_ENGINE_SPEC.md Section 6",
        confidence=_confidence_from_spread(values),
        assumptions=[
            "each input forecast is expressed on the same scale and "
            "answers the same question",
            "the provided historical_errors are a reliable measure of "
            "each model's relative past accuracy",
        ],
        limitations=[
            "weighting by historical error assumes past accuracy "
            "predicts future accuracy, which may not hold if a model's "
            "relative performance has shifted",
        ],
        dependencies=[f.id for f in forecasts],
        disagreement_set_ref=disagreement_set_ref,
    )
