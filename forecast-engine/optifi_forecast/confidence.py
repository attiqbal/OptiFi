"""
Confidence calibration — PHASE E3 brief, Part F: "Do not equate model
agreement with truth." Confidence should consider historical model
performance, recent performance, regime similarity, data quality, model
disagreement, forecast horizon, and out-of-distribution risk. "Do not
create fake precision."

This is the Stage 6 <- Stage 14 feedback loop `ENGINE_PIPELINE_SPECIFICATION.md`
Stage 14's own purpose line names explicitly ("feed evaluation results
back into model confidence calibration") — `forecast-engine` reads
`evaluation-engine`'s `ModelScorecard`s as an input to this function; it
never writes to them, and `evaluation-engine` has no runtime dependency
back on `forecast-engine` (only a dev/test one, for its own examples) —
a one-directional package dependency, not a cycle.

`calibrate_confidence` NEVER returns `ConfidenceLevel.HIGH` — every
factor check below can only downgrade from the MODERATE starting point,
mirroring `ensemble.py`'s own `_confidence_from_spread` and, ultimately,
`UAP`'s own model-level guardrail (`shared/optifi_shared/uap.py`): HIGH
confidence requires a settled VERIFIED/SUPERSEDED status, and a forecast
is an ESTIMATE by definition, never settled in that sense. "Do not
create fake precision" is enforced structurally here the same way.
"""

from __future__ import annotations

from optifi_evaluation import Eligibility, ModelScorecard
from optifi_shared import ConfidenceLevel, ValidationStatus

# Same threshold PHILOSOPHY as ensemble.py's
# _RELATIVE_SPREAD_MODERATE_CONFIDENCE_MAX (0.30) — intentionally aligned
# so "moderate confidence" means the same thing whether it comes from an
# ensemble's own internal spread or from this function's broader
# calibration.
DISAGREEMENT_SPREAD_LOW_CONFIDENCE_THRESHOLD = 0.30

# A horizon phrased in months beyond this is treated as "long" —
# uncertainty compounds enough over a longer horizon that MODERATE is no
# longer defensible. A documented heuristic threshold, not a value fixed
# by any spec document.
LONG_HORIZON_MONTHS_THRESHOLD = 6


def _is_long_horizon(horizon: str) -> bool:
    horizon_lower = horizon.lower().strip()
    if "year" in horizon_lower:
        return True
    if "month" in horizon_lower:
        digits = "".join(ch for ch in horizon_lower.split("-")[0] if ch.isdigit())
        if digits:
            return int(digits) > LONG_HORIZON_MONTHS_THRESHOLD
    return False


def calibrate_confidence(
    scorecard: ModelScorecard | None,
    disagreement_relative_spread: float,
    horizon: str,
    input_validation_status: ValidationStatus,
    is_out_of_distribution: bool = False,
    current_regime: str | None = None,
) -> tuple[ConfidenceLevel, list[str]]:
    """
    Returns `(confidence, reasons)` — `reasons` is never empty, so a
    caller (and eventually a user-facing explanation, Stage 13) can
    always show WHY a given confidence level was assigned, not just the
    level itself. Checked in priority order; the first disqualifying
    factor found short-circuits to LOW rather than accumulating penalties
    into some blended score nothing in the brief asks for.
    """
    if input_validation_status not in (ValidationStatus.VERIFIED, ValidationStatus.SUPERSEDED):
        return ConfidenceLevel.LOW, [
            f"input data validation_status is {input_validation_status.value}, not "
            "VERIFIED/SUPERSEDED — forecasting on unsettled data is a data-quality risk."
        ]

    if is_out_of_distribution:
        return ConfidenceLevel.LOW, [
            "current inputs are flagged out-of-distribution relative to the "
            "model's training range — the model's demonstrated accuracy does "
            "not cover this regime."
        ]

    if scorecard is None:
        return ConfidenceLevel.LOW, [
            "no historical performance scorecard exists for this model/target/"
            "horizon yet — an unproven model cannot be certified at MODERATE confidence."
        ]

    if scorecard.eligibility != Eligibility.ELIGIBLE:
        return ConfidenceLevel.LOW, [
            f"model scorecard eligibility is {scorecard.eligibility.value}, not ELIGIBLE."
        ]

    if current_regime is not None and current_regime in scorecard.regimes_poor:
        return ConfidenceLevel.LOW, [
            f"current regime {current_regime!r} is one this model has "
            "historically performed poorly in (scorecard.regimes_poor)."
        ]

    if disagreement_relative_spread > DISAGREEMENT_SPREAD_LOW_CONFIDENCE_THRESHOLD:
        return ConfidenceLevel.LOW, [
            f"relative disagreement among competing models ({disagreement_relative_spread:.2f}) "
            f"exceeds the moderate-confidence threshold "
            f"({DISAGREEMENT_SPREAD_LOW_CONFIDENCE_THRESHOLD}) — model agreement is not truth, "
            "but strong disagreement is genuine evidence of uncertainty."
        ]

    if _is_long_horizon(horizon):
        return ConfidenceLevel.LOW, [
            f"horizon {horizon!r} exceeds {LONG_HORIZON_MONTHS_THRESHOLD} months — "
            "forecast uncertainty compounds enough over this range that MODERATE is not defensible."
        ]

    return ConfidenceLevel.MODERATE, [
        "model is ELIGIBLE with a demonstrated (baseline-beating) track record, "
        "inputs are VERIFIED, current conditions are in-distribution, model "
        "disagreement is low, and the horizon is short — MODERATE is the ceiling "
        "this function ever returns (see module docstring: never HIGH)."
    ]
