"""
Metrics tests — one per required metric family, plus the "missing
realised outcome" and "miscalibrated probabilities" Testing Requirements.
"""

from datetime import datetime, timezone

import pytest
from optifi_shared import InsufficientDataFailure

from optifi_evaluation import (
    ForecastKind,
    ForecastRecord,
    brier_score,
    direction_classification_metrics,
    evaluate_batch,
    interval_forecast_metrics,
    log_loss_score,
    point_forecast_metrics,
    reliability_curve,
)

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _point(predicted: float, realised: float) -> ForecastRecord:
    return ForecastRecord(
        forecast_packet_id="uap",
        target="t",
        forecast_timestamp=NOW,
        horizon="3-month",
        forecast_kind=ForecastKind.POINT,
        predicted_point=predicted,
        model_id="m",
        model_version="v1",
    ).record_outcome(realised, realised_at=NOW)


def _interval(predicted: float, lower: float, upper: float, realised: float) -> ForecastRecord:
    return ForecastRecord(
        forecast_packet_id="uap",
        target="t",
        forecast_timestamp=NOW,
        horizon="1-month",
        forecast_kind=ForecastKind.INTERVAL,
        predicted_point=predicted,
        predicted_lower=lower,
        predicted_upper=upper,
        model_id="m",
        model_version="v1",
    ).record_outcome(realised, realised_at=NOW)


def _probability(distribution: dict, realised_label: str, predicted_prob_for_realised: float | None = None) -> ForecastRecord:
    return ForecastRecord(
        forecast_packet_id="uap",
        target="t",
        forecast_timestamp=NOW,
        horizon="3-month",
        forecast_kind=ForecastKind.PROBABILITY,
        predicted_distribution=distribution,
        model_id="m",
        model_version="v1",
    ).record_outcome(realised_label, realised_at=NOW)


def _direction(predicted_class: str, realised_class: str) -> ForecastRecord:
    return ForecastRecord(
        forecast_packet_id="uap",
        target="t",
        forecast_timestamp=NOW,
        horizon="1-quarter",
        forecast_kind=ForecastKind.DIRECTION,
        predicted_class=predicted_class,
        model_id="m",
        model_version="v1",
    ).record_outcome(realised_class, realised_at=NOW)


# --- point ---


def test_point_metrics_known_values():
    records = [_point(10.0, 9.0), _point(5.0, 7.0), _point(3.0, 3.0)]
    # errors: +1, -2, 0
    m = point_forecast_metrics(records)
    assert m.mae == pytest.approx((1 + 2 + 0) / 3)
    assert m.rmse == pytest.approx(((1**2 + 2**2 + 0**2) / 3) ** 0.5)
    assert m.bias == pytest.approx((1 - 2 + 0) / 3)
    assert m.n == 3


def test_point_metrics_missing_realised_outcome_raises_insufficient_data():
    """Testing Requirement: 'missing realised outcome' — attempting to
    score a batch that includes a pending (not-yet-due) forecast must
    fail loudly, not silently skip or fabricate a zero error."""
    pending = ForecastRecord(
        forecast_packet_id="uap",
        target="t",
        forecast_timestamp=NOW,
        horizon="3-month",
        forecast_kind=ForecastKind.POINT,
        predicted_point=1.0,
        model_id="m",
        model_version="v1",
    )
    with pytest.raises(InsufficientDataFailure):
        point_forecast_metrics([pending])


def test_evaluate_batch_separates_pending_from_evaluable():
    done = _point(1.0, 1.0)
    pending = ForecastRecord(
        forecast_packet_id="uap2",
        target="t",
        forecast_timestamp=NOW,
        horizon="3-month",
        forecast_kind=ForecastKind.POINT,
        predicted_point=2.0,
        model_id="m",
        model_version="v1",
    )
    result = evaluate_batch([done, pending])
    assert result.evaluable == [done]
    assert result.pending == [pending]


# --- interval ---


def test_interval_metrics_coverage_and_width():
    records = [
        _interval(10.0, 8.0, 12.0, realised=9.0),  # covered, width 4
        _interval(10.0, 9.0, 11.0, realised=15.0),  # not covered, width 2
    ]
    m = interval_forecast_metrics(records)
    assert m.coverage == pytest.approx(0.5)
    assert m.mean_width == pytest.approx(3.0)


# --- probability ---


def test_brier_score_perfect_forecast_is_zero():
    records = [_probability({"falls": 0.0, "flat": 0.0, "rises": 1.0}, "rises")]
    assert brier_score(records) == pytest.approx(0.0)


def test_brier_score_worse_for_confidently_wrong_forecast():
    confidently_wrong = [_probability({"falls": 0.9, "flat": 0.05, "rises": 0.05}, "rises")]
    well_calibrated = [_probability({"falls": 0.33, "flat": 0.34, "rises": 0.33}, "rises")]
    assert brier_score(confidently_wrong) > brier_score(well_calibrated)


def test_log_loss_penalises_confident_wrong_prediction_heavily():
    confidently_wrong = [_probability({"falls": 0.99, "flat": 0.005, "rises": 0.005}, "rises")]
    uncertain = [_probability({"falls": 0.34, "flat": 0.33, "rises": 0.33}, "rises")]
    assert log_loss_score(confidently_wrong) > log_loss_score(uncertain)


def test_reliability_curve_flags_miscalibration():
    """Testing Requirement: 'miscalibrated probabilities' — a model that
    claims ~90% confidence in 'rises' but is only right about half the
    time must show empirical_frequency well below mean_predicted in the
    relevant bin."""
    records = []
    # 10 forecasts all claiming 90% probability of "rises"; only 5 of
    # them actually see "rises" occur.
    for i in range(10):
        realised = "rises" if i < 5 else "falls"
        records.append(_probability({"falls": 0.05, "flat": 0.05, "rises": 0.90}, realised))

    curve = reliability_curve(records, label="rises", n_bins=5)
    top_bin = [b for b in curve if b.n > 0][-1]  # the 0.8-1.0 bin
    assert top_bin.mean_predicted == pytest.approx(0.90)
    assert top_bin.empirical_frequency == pytest.approx(0.5)
    assert top_bin.empirical_frequency < top_bin.mean_predicted - 0.3  # clearly overconfident


def test_reliability_curve_well_calibrated_model_sits_near_diagonal():
    records = []
    for i in range(10):
        realised = "rises" if i < 6 else "falls"  # 60% actually rise
        records.append(_probability({"falls": 0.35, "flat": 0.05, "rises": 0.60}, realised))
    curve = reliability_curve(records, label="rises", n_bins=5)
    populated = [b for b in curve if b.n > 0][0]
    assert abs(populated.mean_predicted - populated.empirical_frequency) < 0.1


# --- direction ---


def test_direction_metrics_accuracy_and_economic_value():
    records = [
        _direction("up", "up"),
        _direction("up", "down"),
        _direction("down", "down"),
        _direction("down", "down"),
    ]
    m = direction_classification_metrics(records)
    assert m.accuracy == pytest.approx(0.75)
    assert m.economic_value_proxy == pytest.approx((1 - 1 + 1 + 1) / 4)
    assert m.precision["down"] == pytest.approx(2 / 2)
    assert m.recall["down"] == pytest.approx(2 / 3)
