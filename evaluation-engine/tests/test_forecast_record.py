"""
ForecastRecord — construction validity, immutability (Part I), and
outcome recording.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from optifi_evaluation import ForecastKind, ForecastRecord

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _point_record(**overrides) -> ForecastRecord:
    defaults = dict(
        forecast_packet_id="uap-1",
        target="test target",
        forecast_timestamp=NOW,
        horizon="3-month",
        forecast_kind=ForecastKind.POINT,
        predicted_point=3.0,
        model_id="test-model",
        model_version="v1",
    )
    defaults.update(overrides)
    return ForecastRecord(**defaults)


# --- shape validation ---


def test_point_forecast_requires_predicted_point():
    with pytest.raises(ValidationError):
        ForecastRecord(
            forecast_packet_id="uap-1",
            target="t",
            forecast_timestamp=NOW,
            horizon="3-month",
            forecast_kind=ForecastKind.POINT,
            model_id="m",
            model_version="v1",
        )


def test_interval_forecast_requires_bounds():
    with pytest.raises(ValidationError):
        ForecastRecord(
            forecast_packet_id="uap-1",
            target="t",
            forecast_timestamp=NOW,
            horizon="1-month",
            forecast_kind=ForecastKind.INTERVAL,
            predicted_point=1.0,
            model_id="m",
            model_version="v1",
        )


def test_probability_distribution_must_sum_to_one():
    with pytest.raises(ValidationError):
        ForecastRecord(
            forecast_packet_id="uap-1",
            target="t",
            forecast_timestamp=NOW,
            horizon="3-month",
            forecast_kind=ForecastKind.PROBABILITY,
            predicted_distribution={"falls": 0.2, "flat": 0.2, "rises": 0.2},
            model_id="m",
            model_version="v1",
        )


def test_valid_probability_distribution_accepted():
    record = ForecastRecord(
        forecast_packet_id="uap-1",
        target="t",
        forecast_timestamp=NOW,
        horizon="3-month",
        forecast_kind=ForecastKind.PROBABILITY,
        predicted_distribution={"falls": 0.2, "flat": 0.5, "rises": 0.3},
        model_id="m",
        model_version="v1",
    )
    assert record.predicted_distribution["flat"] == 0.5


def test_direction_forecast_requires_predicted_class():
    with pytest.raises(ValidationError):
        ForecastRecord(
            forecast_packet_id="uap-1",
            target="t",
            forecast_timestamp=NOW,
            horizon="1-quarter",
            forecast_kind=ForecastKind.DIRECTION,
            model_id="m",
            model_version="v1",
        )


# --- immutability (Part I) ---


def test_forecast_record_is_frozen():
    record = _point_record()
    with pytest.raises(ValidationError):
        record.predicted_point = 999.0


def test_record_outcome_does_not_mutate_original():
    """"If a model changes tomorrow, yesterday's forecast must remain
    exactly as it was" — proven directly: recording an outcome must not
    alter the original object in any way."""
    original = _point_record()
    before = original.model_dump()

    updated = original.record_outcome(2.5, realised_at=NOW)

    after = original.model_dump()
    assert before == after
    assert original.realised_outcome is None
    assert updated.realised_outcome == 2.5
    assert updated is not original


def test_record_outcome_computes_signed_error_for_point():
    record = _point_record(predicted_point=3.0).record_outcome(2.5, realised_at=NOW)
    assert record.error == pytest.approx(0.5)


def test_is_evaluable_false_until_outcome_recorded():
    """The 'missing realised outcome' case — a forecast whose horizon
    hasn't elapsed is a normal, pending state."""
    record = _point_record()
    assert record.is_evaluable() is False
    assert record.record_outcome(3.0).is_evaluable() is True
