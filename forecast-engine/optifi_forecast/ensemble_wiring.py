"""
Wires `evaluation-engine`'s scorecards into `ensemble.py`'s existing
`inverse_error_weighted_ensemble` — PHASE E3 brief, Part G: "compare at
least equal-weight ensemble vs. performance-weighted ensemble." Both
weighting mechanisms already existed before this phase
(`FORECAST_ENGINE_SPEC.md` Section 6, implemented in `ensemble.py`); this
module is the missing link that sources `inverse_error_weighted_ensemble`'s
`historical_errors` argument from real scorecards instead of a caller
having to assemble that list by hand each time.

"A poor-performing model should be capable of losing weight or being
retired" (Part H): a RETIRED model is excluded entirely here (zero
weight, not merely a small one); a PROBATION model is not excluded, but
its own (comparatively worse) historical error naturally gives it a
smaller `inverse_error_weighted_ensemble` weight — no separate
PROBATION-specific penalty is applied on top, since the error-based
weighting already captures it.
"""

from __future__ import annotations

from optifi_evaluation import Eligibility, ModelScorecard
from optifi_shared import InsufficientDataFailure, UAP

from .ensemble import inverse_error_weighted_ensemble


def performance_weighted_ensemble(
    forecasts: list[UAP], model_ids: list[str], scorecards_by_model_id: dict[str, ModelScorecard]
) -> UAP:
    """
    `forecasts` and `model_ids` are parallel lists (same order, same
    length) — `model_ids[i]` identifies which model produced
    `forecasts[i]`. Any forecast whose model has no scorecard on record,
    or whose scorecard is RETIRED, is dropped before weighting.
    """
    if len(forecasts) != len(model_ids):
        raise ValueError(
            f"performance_weighted_ensemble: forecasts ({len(forecasts)}) and "
            f"model_ids ({len(model_ids)}) must be the same length."
        )

    kept_forecasts: list[UAP] = []
    kept_errors: list[float] = []
    dropped: list[str] = []
    for forecast, model_id in zip(forecasts, model_ids, strict=True):
        scorecard = scorecards_by_model_id.get(model_id)
        if scorecard is None or scorecard.eligibility == Eligibility.RETIRED:
            dropped.append(model_id)
            continue
        kept_forecasts.append(forecast)
        kept_errors.append(scorecard.primary_metric_value)

    if len(kept_forecasts) < 2:
        raise InsufficientDataFailure(
            "performance_weighted_ensemble: fewer than 2 non-retired, "
            f"scorecard-backed models remain ({len(kept_forecasts)} of "
            f"{len(forecasts)}; dropped: {dropped!r}) — cannot build a "
            "meaningful performance-weighted ensemble."
        )
    return inverse_error_weighted_ensemble(kept_forecasts, kept_errors)
