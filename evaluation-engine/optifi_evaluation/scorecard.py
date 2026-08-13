"""
Model scorecards and eligibility — PHASE E3 brief, Part H: "Each
forecasting model should have an auditable scorecard... A poor-performing
model should be capable of losing weight or being retired."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class Eligibility(str, Enum):
    """A scorecard's current standing. `forecast-engine`'s
    performance-weighted ensemble (Part G) should exclude anything other
    than ELIGIBLE — see `registry.eligible_scorecards`."""

    ELIGIBLE = "ELIGIBLE"
    PROBATION = "PROBATION"  # underperforms its own baseline, not yet retired
    RETIRED = "RETIRED"  # materially worse than baseline — should not be used
    STALE = "STALE"  # not evaluated recently enough to trust the standing figures


# Calibration constants — documented, not derived from any spec figure.
# A model whose primary metric is more than this multiple worse than its
# own baseline's is RETIRED outright rather than merely PROBATION; between
# 1.0x and this multiple, it is degraded but not cut off (a model that is
# only marginally worse than a naive baseline may still add ensemble
# diversity value, per FORECAST_ENGINE_SPEC.md Section 6's framing that
# disagreement itself is informative — pure underperformance vs. gross
# underperformance are treated differently).
RETIREMENT_MULTIPLE = 1.5
# Default staleness window: if a scorecard's last_evaluation is older than
# this relative to "now", its own performance figures are treated as too
# old to certify current eligibility — mirrors data-engine's own staleness
# discipline (ingestion.py's DEFAULT_STALENESS_THRESHOLD), applied here to
# MODEL performance rather than raw data.
DEFAULT_SCORECARD_STALENESS = timedelta(days=90)


@dataclass(frozen=True)
class ModelScorecard:
    """
    An auditable record of one model's demonstrated performance —
    Part H's required fields verbatim: model id/version, target, horizon,
    training window, evaluation period, performance metrics, regimes
    where it performs well/poorly, last evaluation, current eligibility.

    Frozen for the same "immutable historical record" reason as
    `ForecastRecord` — a scorecard is itself evidence, re-evaluation
    produces a NEW scorecard (see `registry.build_scorecard`), it does
    not silently overwrite the old one.
    """

    model_id: str
    model_version: str
    target: str
    horizon: str
    training_window: tuple[datetime, datetime]
    evaluation_period: tuple[datetime, datetime]
    primary_metric_name: str
    primary_metric_value: float
    higher_is_better: bool
    baseline_metric_value: float | None
    n_evaluated: int
    regimes_good: tuple[str, ...] = field(default_factory=tuple)
    regimes_poor: tuple[str, ...] = field(default_factory=tuple)
    last_evaluation: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    eligibility: Eligibility = Eligibility.ELIGIBLE

    def beats_baseline(self) -> bool | None:
        """None if no baseline was supplied to compare against — a
        model cannot be certified as adding value without one (Part B:
        "A complicated model that cannot beat a simple baseline adds no
        demonstrated value")."""
        if self.baseline_metric_value is None:
            return None
        if self.higher_is_better:
            return self.primary_metric_value > self.baseline_metric_value
        return self.primary_metric_value < self.baseline_metric_value


def determine_eligibility(
    primary_metric_value: float,
    baseline_metric_value: float | None,
    higher_is_better: bool,
    last_evaluation: datetime,
    now: datetime,
    staleness_threshold: timedelta = DEFAULT_SCORECARD_STALENESS,
) -> Eligibility:
    """
    Pure eligibility decision, in priority order:

    1. STALE overrides everything else — a performance figure too old to
       trust is not a basis to claim ELIGIBLE, however good it once was.
    2. No baseline supplied -> conservatively PROBATION, never ELIGIBLE —
       Part B's own rule means "beats baseline" must be demonstrated, not
       assumed absent evidence.
    3. Fails to beat baseline at all -> PROBATION.
    4. Fails baseline by more than RETIREMENT_MULTIPLE -> RETIRED.
    5. Otherwise -> ELIGIBLE.
    """
    if now - last_evaluation > staleness_threshold:
        return Eligibility.STALE

    if baseline_metric_value is None:
        return Eligibility.PROBATION

    if higher_is_better:
        beats = primary_metric_value > baseline_metric_value
        ratio = (baseline_metric_value / primary_metric_value) if primary_metric_value > 0 else float("inf")
    else:
        beats = primary_metric_value < baseline_metric_value
        ratio = (primary_metric_value / baseline_metric_value) if baseline_metric_value > 0 else float("inf")

    if not beats and ratio >= RETIREMENT_MULTIPLE:
        return Eligibility.RETIRED
    if not beats:
        return Eligibility.PROBATION
    return Eligibility.ELIGIBLE
