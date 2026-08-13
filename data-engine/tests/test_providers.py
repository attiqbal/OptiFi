"""
Tests for the provider abstraction and FixtureProvider (Phase E2).
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from optifi_shared import MissingInputFailure, SourceIdentity

from optifi_data.providers import (
    DataCategory,
    FeedLatency,
    FixtureProvider,
    ObservationRequest,
    ProviderAdapter,
    ProviderUnavailableFailure,
    RawPayload,
)

FIXTURE_DIR = Path(__file__).parent.parent / "optifi_data" / "fixtures"


def test_fetch_latest_market_observation():
    provider = FixtureProvider(FIXTURE_DIR)
    payload = provider.fetch(ObservationRequest(category=DataCategory.MARKET, identifier="SYNTH_ACME"))
    assert payload.raw_data["price"] == 100.87  # the last (most recent) record in the fixture
    assert payload.provider_name == "fixture-provider"


def test_fetch_point_in_time_market_observation():
    provider = FixtureProvider(FIXTURE_DIR)
    payload = provider.fetch(
        ObservationRequest(
            category=DataCategory.MARKET,
            identifier="SYNTH_ACME",
            as_of=datetime(2026, 8, 1, 16, 30, tzinfo=timezone.utc),
        )
    )
    assert payload.raw_data["price"] == 101.23


def test_fetch_macro_observation():
    provider = FixtureProvider(FIXTURE_DIR)
    payload = provider.fetch(ObservationRequest(category=DataCategory.MACRO, identifier="SYNTH_CPI"))
    assert payload.raw_data["indicator_name"] == "SYNTH_CPI_YOY"


def test_fetch_event():
    provider = FixtureProvider(FIXTURE_DIR)
    payload = provider.fetch(ObservationRequest(category=DataCategory.EVENT, identifier="SYNTH_EARNINGS"))
    assert payload.raw_data["event_type"] == "earnings_release"


def test_source_identity_is_parsed_from_the_fixture_record():
    """Test category #7 (required): source provenance — the raw
    payload's source_identity must be a real, structured SourceIdentity,
    not a bare string, and must reflect what the fixture actually says."""
    provider = FixtureProvider(FIXTURE_DIR)
    payload = provider.fetch(ObservationRequest(category=DataCategory.MARKET, identifier="SYNTH_ACME"))
    assert isinstance(payload.source_identity, SourceIdentity)
    assert payload.source_identity.publication == "Illustrative Test Market Data Vendor"
    assert payload.source_identity.originating_document_id == "synth-acme-2026-08-03"


# --- API/source failure (required test category #2) ---


def test_missing_fixture_raises_missing_input_failure_not_a_silent_empty_result():
    provider = FixtureProvider(FIXTURE_DIR)
    with pytest.raises(MissingInputFailure):
        provider.fetch(ObservationRequest(category=DataCategory.MARKET, identifier="SYNTH_DOES_NOT_EXIST"))


def test_no_record_at_requested_as_of_raises_missing_input_failure():
    provider = FixtureProvider(FIXTURE_DIR)
    with pytest.raises(MissingInputFailure):
        provider.fetch(
            ObservationRequest(
                category=DataCategory.MARKET,
                identifier="SYNTH_ACME",
                as_of=datetime(1999, 1, 1, tzinfo=timezone.utc),
            )
        )


# --- provider replacement (required test category #5) ---


class _AlwaysFailsProvider(ProviderAdapter):
    """A second, independent ProviderAdapter implementation used only
    to prove the ingestion pipeline genuinely depends on the interface,
    not on FixtureProvider specifically."""

    provider_name = "always-fails-test-provider"
    latency_class = FeedLatency.REAL_TIME

    def fetch(self, request: ObservationRequest) -> RawPayload:
        raise ProviderUnavailableFailure("simulated outage", retry_after_seconds=30.0)


class _StaticStubProvider(ProviderAdapter):
    """A third ProviderAdapter, returning a fixed record regardless of
    request — proves a caller can swap providers freely."""

    provider_name = "static-stub-provider"
    latency_class = FeedLatency.END_OF_DAY

    def fetch(self, request: ObservationRequest) -> RawPayload:
        return RawPayload(
            raw_data={"instrument_id": request.identifier, "price": 999.0, "currency": "USD"},
            provider_name=self.provider_name,
            source_identity=SourceIdentity(publication="Static Stub"),
            latency_class=self.latency_class,
        )


def test_provider_can_be_swapped_without_changing_the_calling_code():
    def _get_latest_price(provider: ProviderAdapter, instrument_id: str) -> float:
        payload = provider.fetch(ObservationRequest(category=DataCategory.MARKET, identifier=instrument_id))
        return payload.raw_data["price"]

    fixture_price = _get_latest_price(FixtureProvider(FIXTURE_DIR), "SYNTH_ACME")
    stub_price = _get_latest_price(_StaticStubProvider(), "SYNTH_ACME")

    assert fixture_price == 100.87
    assert stub_price == 999.0
    # Same calling code, same interface, genuinely different providers —
    # this is the "changing a provider should not require rewriting
    # downstream code" property, proven directly.


def test_provider_unavailable_is_a_distinct_failure_from_missing_data():
    """Test category #11 (required): rate-limit/degraded behaviour.
    ProviderUnavailableFailure (can't reach the source at all) must be
    distinguishable from MissingInputFailure (reached it, no data)."""
    provider = _AlwaysFailsProvider()
    with pytest.raises(ProviderUnavailableFailure) as exc_info:
        provider.fetch(ObservationRequest(category=DataCategory.MARKET, identifier="SYNTH_ACME"))
    assert exc_info.value.retry_after_seconds == 30.0
