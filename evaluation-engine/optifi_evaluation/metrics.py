"""
Target-appropriate evaluation metrics (PHASE E3 brief, Part E: "Evaluation
Metrics" — "Do not apply one metric to every forecasting problem.").

Four families, matching `ForecastRecord.forecast_kind`:

- **Point** (`point_forecast_metrics`): MAE, RMSE, bias.
- **Interval** (`interval_forecast_metrics`): coverage, mean interval width.
- **Probability** (`brier_score`, `log_loss_score`, `reliability_curve`):
  Brier score, log loss, and a reliability/calibration curve.
- **Direction** (`direction_classification_metrics`): accuracy,
  precision/recall, and a simplified economic-value proxy.

Every function requires every input record be evaluable
(`ForecastRecord.is_evaluable()`); the caller is expected to have already
separated "not yet due" forecasts out (the "missing realised outcome"
Testing Requirement — see `evaluate_batch` in this module, which does that
separation explicitly rather than each metric function silently doing it
differently).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from optifi_shared import InsufficientDataFailure

from .forecast_record import ForecastKind, ForecastRecord

# Log loss clipping: an exact 0.0 or 1.0 predicted probability makes
# log(0) undefined. Clip to this epsilon on both ends, matching the
# standard scikit-learn-style convention, rather than let one
# overconfident zero-probability prediction produce an infinite score
# that swamps every other record's contribution.
_LOG_LOSS_EPSILON = 1e-12


def _require_evaluable(records: list[ForecastRecord], fn_name: str) -> list[ForecastRecord]:
    if not records:
        raise InsufficientDataFailure(f"{fn_name}: no records supplied.")
    not_evaluable = [r for r in records if not r.is_evaluable()]
    if not_evaluable:
        raise InsufficientDataFailure(
            f"{fn_name}: {len(not_evaluable)} of {len(records)} record(s) have no "
            "realised_outcome recorded yet — call evaluate_batch() first to "
            "separate pending forecasts out, or record_outcome() on each."
        )
    return records


@dataclass(frozen=True)
class BatchEvaluation:
    """Split of a batch into what can and cannot be scored right now —
    the "missing realised outcome" case made explicit rather than an
    error."""

    evaluable: list[ForecastRecord]
    pending: list[ForecastRecord]


def evaluate_batch(records: list[ForecastRecord]) -> BatchEvaluation:
    """Separates `records` into evaluable (realised outcome known) and
    pending (horizon not yet elapsed / outcome not yet recorded) —
    pending is a normal state, not a failure."""
    evaluable = [r for r in records if r.is_evaluable()]
    pending = [r for r in records if not r.is_evaluable()]
    return BatchEvaluation(evaluable=evaluable, pending=pending)


# --- Point forecasts ---


@dataclass(frozen=True)
class PointMetrics:
    mae: float
    rmse: float
    bias: float
    n: int


def point_forecast_metrics(records: list[ForecastRecord]) -> PointMetrics:
    records = _require_evaluable(records, "point_forecast_metrics")
    for r in records:
        if r.forecast_kind not in (ForecastKind.POINT, ForecastKind.INTERVAL):
            raise ValueError(
                f"point_forecast_metrics: record {r.id!r} has forecast_kind="
                f"{r.forecast_kind!r}, not POINT/INTERVAL."
            )
    errors = [r.error for r in records]
    n = len(errors)
    mae = sum(abs(e) for e in errors) / n
    rmse = math.sqrt(sum(e * e for e in errors) / n)
    bias = sum(errors) / n
    return PointMetrics(mae=mae, rmse=rmse, bias=bias, n=n)


# --- Interval forecasts ---


@dataclass(frozen=True)
class IntervalMetrics:
    coverage: float
    mean_width: float
    n: int


def interval_forecast_metrics(records: list[ForecastRecord]) -> IntervalMetrics:
    records = _require_evaluable(records, "interval_forecast_metrics")
    for r in records:
        if r.forecast_kind != ForecastKind.INTERVAL:
            raise ValueError(f"interval_forecast_metrics: record {r.id!r} is not INTERVAL.")
    n = len(records)
    covered = sum(
        1 for r in records if r.predicted_lower <= float(r.realised_outcome) <= r.predicted_upper
    )
    widths = [r.predicted_upper - r.predicted_lower for r in records]
    return IntervalMetrics(coverage=covered / n, mean_width=sum(widths) / n, n=n)


# --- Probability forecasts ---


def _probability_of_realised(record: ForecastRecord) -> float:
    label = record.realised_outcome
    if label not in record.predicted_distribution:
        raise ValueError(
            f"_probability_of_realised: realised_outcome {label!r} is not one of "
            f"this record's predicted_distribution buckets {sorted(record.predicted_distribution)!r}."
        )
    return record.predicted_distribution[label]


def brier_score(records: list[ForecastRecord]) -> float:
    """Multi-class Brier score: mean over records and buckets of
    (predicted_prob - actual_indicator)^2. 0.0 is perfect; a
    K-bucket forecaster with no skill scores around 2*(K-1)/K^2 for a
    uniform-random truth (not a fixed universal constant to assert
    against — depends on K and the true class-frequency distribution)."""
    records = _require_evaluable(records, "brier_score")
    for r in records:
        if r.forecast_kind != ForecastKind.PROBABILITY:
            raise ValueError(f"brier_score: record {r.id!r} is not PROBABILITY.")
    total = 0.0
    n_terms = 0
    for r in records:
        for label, p in r.predicted_distribution.items():
            actual = 1.0 if label == r.realised_outcome else 0.0
            total += (p - actual) ** 2
            n_terms += 1
    return total / len(records) if records else 0.0


def log_loss_score(records: list[ForecastRecord]) -> float:
    records = _require_evaluable(records, "log_loss_score")
    for r in records:
        if r.forecast_kind != ForecastKind.PROBABILITY:
            raise ValueError(f"log_loss_score: record {r.id!r} is not PROBABILITY.")
    losses = []
    for r in records:
        p = _probability_of_realised(r)
        p_clipped = min(max(p, _LOG_LOSS_EPSILON), 1.0 - _LOG_LOSS_EPSILON)
        losses.append(-math.log(p_clipped))
    return sum(losses) / len(losses)


@dataclass(frozen=True)
class ReliabilityBin:
    bin_lower: float
    bin_upper: float
    mean_predicted: float | None
    empirical_frequency: float | None
    n: int


def reliability_curve(records: list[ForecastRecord], label: str, n_bins: int = 5) -> list[ReliabilityBin]:
    """
    Calibration check (Part F / Testing Requirements — "miscalibrated
    probabilities"): buckets this label's predicted probability into
    `n_bins` equal-width bins and compares the mean predicted probability
    in each bin against how often `label` actually occurred among the
    forecasts landing in that bin. A well-calibrated model's points sit
    near the diagonal (mean_predicted ~= empirical_frequency); systematic
    overconfidence shows as empirical_frequency well below mean_predicted.
    """
    records = _require_evaluable(records, "reliability_curve")
    for r in records:
        if r.forecast_kind != ForecastKind.PROBABILITY:
            raise ValueError(f"reliability_curve: record {r.id!r} is not PROBABILITY.")
        if label not in r.predicted_distribution:
            raise ValueError(f"reliability_curve: label {label!r} not in record {r.id!r}'s distribution.")

    bin_width = 1.0 / n_bins
    bins: list[ReliabilityBin] = []
    for i in range(n_bins):
        lower, upper = i * bin_width, (i + 1) * bin_width
        in_bin = [r for r in records if lower <= r.predicted_distribution[label] < upper or (upper == 1.0 and r.predicted_distribution[label] == 1.0)]
        if not in_bin:
            bins.append(ReliabilityBin(lower, upper, None, None, 0))
            continue
        mean_predicted = sum(r.predicted_distribution[label] for r in in_bin) / len(in_bin)
        empirical = sum(1 for r in in_bin if r.realised_outcome == label) / len(in_bin)
        bins.append(ReliabilityBin(lower, upper, mean_predicted, empirical, len(in_bin)))
    return bins


# --- Direction / classification forecasts ---


@dataclass(frozen=True)
class DirectionMetrics:
    accuracy: float
    precision: dict[str, float]
    recall: dict[str, float]
    economic_value_proxy: float
    n: int


def direction_classification_metrics(records: list[ForecastRecord]) -> DirectionMetrics:
    """
    `economic_value_proxy`: a SIMPLIFIED stand-in, not a real backtested
    P&L — +1 for a correct directional call, -1 for an incorrect one,
    averaged. A genuine economic-value metric would need real position
    sizing, transaction costs, and realised returns, none of which this
    project has connected (no live market data — DATA_SOURCE_REGISTRY.md
    Section 7.1). Documented here rather than presented as a real return
    figure, per this project's "never fabricate unavailable financial
    information" rule.
    """
    records = _require_evaluable(records, "direction_classification_metrics")
    for r in records:
        if r.forecast_kind != ForecastKind.DIRECTION:
            raise ValueError(f"direction_classification_metrics: record {r.id!r} is not DIRECTION.")

    n = len(records)
    correct = sum(1 for r in records if r.predicted_class == r.realised_outcome)
    accuracy = correct / n

    labels = sorted({r.predicted_class for r in records} | {r.realised_outcome for r in records})
    precision: dict[str, float] = {}
    recall: dict[str, float] = {}
    for label in labels:
        predicted_positive = [r for r in records if r.predicted_class == label]
        actual_positive = [r for r in records if r.realised_outcome == label]
        true_positive = sum(1 for r in predicted_positive if r.realised_outcome == label)
        precision[label] = true_positive / len(predicted_positive) if predicted_positive else float("nan")
        recall[label] = true_positive / len(actual_positive) if actual_positive else float("nan")

    economic_value_proxy = sum(1.0 if r.predicted_class == r.realised_outcome else -1.0 for r in records) / n

    return DirectionMetrics(
        accuracy=accuracy, precision=precision, recall=recall, economic_value_proxy=economic_value_proxy, n=n
    )
