"""
Tests for Stage 2 validation (Phase E2).
"""

from datetime import datetime, timedelta, timezone

from optifi_shared import SourceIdentity

from optifi_data.providers import FeedLatency, RawPayload
from optifi_data.validation import (
    validate_macro_observation,
    validate_market_observation,
    validate_structured_event,
)

NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)


def _market_payload(**overrides) -> RawPayload:
    data = {
        "instrument_id": "SYNTH_ACME",
        "price": 100.0,
        "currency": "GBP",
        "observation_time": "2026-08-03T16:30:00+00:00",
    }
    data.update(overrides)
    return RawPayload(
        raw_data=data,
        provider_name="test-provider",
        source_identity=SourceIdentity(publication="Test Vendor"),
        latency_class=FeedLatency.END_OF_DAY,
        retrieved_at=NOW,
    )


# --- market observation ---


def test_valid_market_observation_passes_with_no_issues():
    obs, issues = validate_market_observation(
        _market_payload(), expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert issues == []
    assert obs.price == 100.0


def test_missing_price_is_flagged_not_silently_defaulted():
    """Required test category #1 (successful ingestion contrast) /
    missing observations."""
    payload = _market_payload(price=None)
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    assert any(i.category == "IMPOSSIBLE_VALUE" for i in issues)


def test_negative_price_is_an_impossible_value():
    payload = _market_payload(price=-5.0)
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    assert any(i.category == "IMPOSSIBLE_VALUE" for i in issues)


def test_zero_price_is_an_impossible_value():
    payload = _market_payload(price=0.0)
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    assert any(i.category == "IMPOSSIBLE_VALUE" for i in issues)


def test_currency_mismatch_is_flagged():
    """Required test category #9: unit/currency normalisation."""
    payload = _market_payload(currency="USD")
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    assert any(i.category == "CURRENCY_MISMATCH" for i in issues)


def test_stale_observation_is_flagged():
    """Required test category #3: stale observation."""
    old_payload = _market_payload(observation_time="2026-01-01T16:30:00+00:00")
    obs, issues = validate_market_observation(
        old_payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    assert any(i.category == "STALE_INPUT" for i in issues)


def test_observation_within_staleness_threshold_is_not_flagged_stale():
    payload = _market_payload(observation_time="2026-08-03T16:30:00+00:00")
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert not any(i.category == "STALE_INPUT" for i in issues)


def test_discontinuity_flagged_on_large_relative_price_move():
    obs, issues = validate_market_observation(
        _market_payload(price=200.0),
        expected_currency="GBP",
        now=NOW,
        staleness_threshold=timedelta(days=5),
        previous_price=100.0,
    )
    assert obs is None
    assert any(i.category == "DISCONTINUITY" for i in issues)


def test_small_price_move_is_not_a_discontinuity():
    obs, issues = validate_market_observation(
        _market_payload(price=101.0),
        expected_currency="GBP",
        now=NOW,
        staleness_threshold=timedelta(days=5),
        previous_price=100.0,
    )
    assert not any(i.category == "DISCONTINUITY" for i in issues)


def test_weekend_observation_time_is_a_calendar_mismatch():
    # 2026-08-01 is a Saturday.
    payload = _market_payload(observation_time="2026-08-01T16:30:00+00:00")
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    assert any(i.category == "CALENDAR_MISMATCH" for i in issues)


def test_retrieved_before_observed_is_a_timestamp_inconsistency():
    payload = _market_payload(observation_time="2026-08-03T16:30:00+00:00")
    payload = payload.model_copy(update={"retrieved_at": datetime(2026, 8, 1, tzinfo=timezone.utc)})
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    assert any(i.category == "TIMESTAMP_INCONSISTENCY" for i in issues)


def test_multiple_simultaneous_issues_are_all_reported_not_just_the_first():
    payload = _market_payload(price=-5.0, currency="USD")
    obs, issues = validate_market_observation(
        payload, expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=5)
    )
    assert obs is None
    categories = {i.category for i in issues}
    assert "IMPOSSIBLE_VALUE" in categories
    assert "CURRENCY_MISMATCH" in categories


# --- macro observation ---


def _macro_payload(**overrides) -> RawPayload:
    data = {
        "indicator_name": "SYNTH_CPI_YOY",
        "value": 3.1,
        "unit": "%",
        "observation_time": "2026-07-15T09:30:00+00:00",
    }
    data.update(overrides)
    return RawPayload(
        raw_data=data,
        provider_name="test-provider",
        source_identity=SourceIdentity(publication="Test Statistics Office"),
        latency_class=FeedLatency.PERIODIC_RELEASE,
        retrieved_at=NOW,
    )


def test_valid_macro_observation_passes():
    obs, issues = validate_macro_observation(_macro_payload(), now=NOW, staleness_threshold=timedelta(days=60))
    assert issues == []
    assert obs.value == 3.1


def test_macro_missing_value_is_flagged():
    obs, issues = validate_macro_observation(
        _macro_payload(value=None), now=NOW, staleness_threshold=timedelta(days=60)
    )
    assert obs is None
    assert any(i.category == "IMPOSSIBLE_VALUE" for i in issues)


def test_macro_negative_value_is_not_flagged_deflation_is_legitimate():
    """A negative macro value (e.g. deflation) is NOT universally
    impossible, unlike a negative price — confirms no over-broad range
    check was accidentally applied."""
    obs, issues = validate_macro_observation(
        _macro_payload(value=-0.5), now=NOW, staleness_threshold=timedelta(days=60)
    )
    assert issues == []
    assert obs.value == -0.5


# --- structured event ---


def _event_payload(**overrides) -> RawPayload:
    data = {
        "event_type": "earnings_release",
        "description": "Test event",
        "entity_ids": ["entity-1"],
        "observation_time": "2026-07-28T07:00:00+00:00",
    }
    data.update(overrides)
    return RawPayload(
        raw_data=data,
        provider_name="test-provider",
        source_identity=SourceIdentity(publication="Test Co"),
        latency_class=FeedLatency.PERIODIC_RELEASE,
        retrieved_at=NOW,
    )


def test_valid_structured_event_passes():
    obs, issues = validate_structured_event(_event_payload())
    assert issues == []
    assert obs.event_type == "earnings_release"


def test_event_missing_description_is_flagged():
    obs, issues = validate_structured_event(_event_payload(description=None))
    assert obs is None
    assert any(i.category == "IMPOSSIBLE_VALUE" for i in issues)
