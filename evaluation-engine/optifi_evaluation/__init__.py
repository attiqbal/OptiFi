"""
optifi_evaluation — evaluation-engine.

Owns Stage 14 (Outcome Tracking & Model Evaluation) — see this package's
README.md and `ENGINE_PIPELINE_SPECIFICATION.md` Section 12 item 1 for the
ownership decision.
"""

from .forecast_record import ForecastKind, ForecastRecord
from .metrics import (
    BatchEvaluation,
    brier_score,
    direction_classification_metrics,
    DirectionMetrics,
    evaluate_batch,
    interval_forecast_metrics,
    IntervalMetrics,
    log_loss_score,
    point_forecast_metrics,
    PointMetrics,
    reliability_curve,
    ReliabilityBin,
)
from .registry import build_scorecard, ModelRegistry
from .scorecard import (
    DEFAULT_SCORECARD_STALENESS,
    determine_eligibility,
    Eligibility,
    ModelScorecard,
    RETIREMENT_MULTIPLE,
)
from .vintage_consistency import check_vintage_consistency, VintageCheckResult

__all__ = [
    "ForecastKind",
    "ForecastRecord",
    "BatchEvaluation",
    "evaluate_batch",
    "point_forecast_metrics",
    "PointMetrics",
    "interval_forecast_metrics",
    "IntervalMetrics",
    "brier_score",
    "log_loss_score",
    "reliability_curve",
    "ReliabilityBin",
    "direction_classification_metrics",
    "DirectionMetrics",
    "ModelScorecard",
    "Eligibility",
    "determine_eligibility",
    "DEFAULT_SCORECARD_STALENESS",
    "RETIREMENT_MULTIPLE",
    "ModelRegistry",
    "build_scorecard",
    "check_vintage_consistency",
    "VintageCheckResult",
]
