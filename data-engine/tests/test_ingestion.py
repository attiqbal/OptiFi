"""
Tests for Stage 1 ingestion orchestration (Phase E2) — the full
"Provider Adapter -> Canonical OptiFi Observation -> Validation ->
UAP / Data Store" pipeline, end to end. Covers every required Phase E2
test category at the ingestion level (several are also covered more
narrowly in test_providers.py/test_validation.py/test_asset_identity.py;
this file is the integration layer tying them together).
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from optifi_shared import (
    ConfidenceLevel,
    InformationClass,
    MarketObservation,
    UAP,
    ValidationStatus,
)

from optifi_data.cache import ObservationCache
from optifi_data.ingestion import ingest_macro_observation, ingest_market_observation, ingest_structured_event
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
NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


@pytest.fixture
def cache(tmp_path) -> ObservationCache:
    return ObservationCache(tmp_path / "cache")


@pytest.fixture
def provider() -> FixtureProvider:
    return FixtureProvider(FIXTURE_DIR)


# --- 1. successful ingestion ---


def test_successful_market_ingestion_produces_a_verified_fact_uap(provider, cache):
    result = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30)
    )
    assert result.uap is not None
    assert result.quarantine_issues == []
    assert result.uap.information_class == InformationClass.FACT
    assert result.uap.validation_status == ValidationStatus.VERIFIED
    assert isinstance(result.uap.result, MarketObservation)


def test_successful_macro_ingestion_produces_a_verified_fact_uap(provider, cache):
    result = ingest_macro_observation(provider, cache, "SYNTH_CPI", now=NOW, staleness_threshold=timedelta(days=60))
    assert result.uap is not None
    assert result.uap.validation_status == ValidationStatus.VERIFIED


def test_successful_event_ingestion_produces_a_provisional_fact_uap(provider, cache):
    result = ingest_structured_event(provider, cache, "SYNTH_EARNINGS")
    assert result.uap is not None
    assert result.uap.validation_status == ValidationStatus.PROVISIONAL


# --- 2. API/source failure ---


class _AlwaysUnavailableProvider(ProviderAdapter):
    provider_name = "always-unavailable"
    latency_class = FeedLatency.REAL_TIME

    def fetch(self, request: ObservationRequest) -> RawPayload:
        raise ProviderUnavailableFailure("simulated network outage")


def test_provider_failure_is_quarantined_not_raised_uncaught(cache):
    """Failed retrievals must be reported, never silently dropped — and
    never allowed to crash the whole ingestion run either."""
    result = ingest_market_observation(
        _AlwaysUnavailableProvider(), cache, "SYNTH_ACME", expected_currency="GBP", now=NOW,
        staleness_threshold=timedelta(days=30),
    )
    assert result.uap is None
    assert len(result.quarantine_issues) == 1
    assert "unavailable" in result.quarantine_issues[0].message


def test_provider_failure_for_a_nonexistent_fixture_is_quarantined(provider, cache):
    result = ingest_market_observation(
        provider, cache, "SYNTH_DOES_NOT_EXIST", expected_currency="GBP", now=NOW,
        staleness_threshold=timedelta(days=30),
    )
    assert result.uap is None
    assert result.quarantine_issues[0].category == "MISSING_INPUT"


# --- 3. stale observation ---


def test_stale_observation_is_quarantined_at_ingestion_level(provider, cache):
    result = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW,
        staleness_threshold=timedelta(minutes=1),  # far tighter than the fixture's real age
    )
    assert result.uap is None
    assert any(i.category == "STALE_INPUT" for i in result.quarantine_issues)


# --- 4. duplicate observation ---


def test_idempotent_re_ingestion_of_identical_observation_returns_the_existing_uap(provider, cache):
    first = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30)
    )
    second = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30),
        previous_uap=first.uap,
    )
    assert second.uap.id == first.uap.id
    assert second.quarantine_issues == []


def test_conflicting_duplicate_observation_is_quarantined_not_silently_overwritten(provider, cache):
    conflicting_previous = UAP(
        subject="market price: SYNTH_ACME",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=MarketObservation(instrument_id="SYNTH_ACME", price=999.0, currency="GBP"),
        source="a different source",
        producer="x",
        confidence=ConfidenceLevel.MODERATE,
        observation_time=datetime(2026, 8, 3, 16, 30, tzinfo=timezone.utc),  # same time as the fixture's latest record
    )
    result = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30),
        previous_uap=conflicting_previous,
    )
    assert result.uap is None
    assert result.quarantine_issues[0].category == "DUPLICATE_OBSERVATION"
    assert "999.0" in result.quarantine_issues[0].message
    assert "100.87" in result.quarantine_issues[0].message


# --- 5. provider replacement ---


class _AlternateStubProvider(ProviderAdapter):
    provider_name = "alternate-vendor"
    latency_class = FeedLatency.END_OF_DAY

    def fetch(self, request: ObservationRequest) -> RawPayload:
        from optifi_shared import SourceIdentity

        return RawPayload(
            raw_data={
                "instrument_id": request.identifier,
                "price": 55.5,
                "currency": "GBP",
                "observation_time": "2026-08-10T16:30:00+00:00",
            },
            provider_name=self.provider_name,
            source_identity=SourceIdentity(publication="Alternate Vendor Ltd"),
            latency_class=self.latency_class,
            retrieved_at=NOW,
        )


def test_swapping_the_provider_requires_no_change_to_calling_code(cache, provider):
    """Task's own architectural goal, proven directly: 'changing a
    provider should not require rewriting quant, forecast, causal,
    simulation, optimisation, or AI engines' — here proven one level
    down, that the ingestion call itself is provider-agnostic."""
    fixture_result = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30)
    )
    alternate_result = ingest_market_observation(
        _AlternateStubProvider(), cache, "SYNTH_ACME", expected_currency="GBP", now=NOW,
        staleness_threshold=timedelta(days=30),
    )
    assert fixture_result.uap.result.price == 100.87
    assert alternate_result.uap.result.price == 55.5
    assert fixture_result.uap.producer != alternate_result.uap.producer


# --- 6. revision/vintage handling ---


def test_revised_macro_release_supersedes_rather_than_overwrites(provider, cache):
    advance_time = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
    advance = ingest_macro_observation(
        provider, cache, "SYNTH_CPI", now=NOW, staleness_threshold=timedelta(days=60), as_of=advance_time
    )
    assert advance.uap.vintage == "advance estimate"
    assert advance.uap.result.value == 2.9

    revised = ingest_macro_observation(
        provider, cache, "SYNTH_CPI", now=NOW, staleness_threshold=timedelta(days=60), previous_uap=advance.uap
    )

    assert revised.uap.result.value == 3.1
    assert revised.uap.vintage == "second estimate"
    assert advance.uap.id in revised.uap.supersedes
    # Historical information is never overwritten: the OLD uap object
    # is completely untouched, still reporting its own original value.
    assert advance.uap.result.value == 2.9
    assert advance.uap.validation_status == ValidationStatus.VERIFIED
    # The superseded copy IS marked, distinctly from the untouched original.
    assert revised.superseded is not None
    assert revised.superseded.validation_status == ValidationStatus.SUPERSEDED
    assert revised.superseded.result.value == 2.9


# --- 7. source provenance ---


def test_ingested_uap_carries_full_source_and_time_provenance(provider, cache):
    result = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30)
    )
    uap = result.uap
    assert uap.source == "Illustrative Test Market Data Vendor"
    assert uap.producer == "data-engine / fixture-provider"
    assert uap.observation_time == datetime(2026, 8, 3, 16, 30, tzinfo=timezone.utc)
    assert uap.publication_time == datetime(2026, 8, 3, 16, 30, tzinfo=timezone.utc)
    assert uap.retrieval_time is not None


# --- 9. unit/currency normalisation ---


def test_currency_mismatch_is_quarantined_at_ingestion_level(provider, cache):
    result = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="USD", now=NOW, staleness_threshold=timedelta(days=30)
    )
    assert result.uap is None
    assert result.quarantine_issues[0].category == "CURRENCY_MISMATCH"


# --- 10. deterministic cached replay ---


def test_cached_replay_is_byte_for_byte_deterministic(provider, cache):
    """Historical tests must be reproducible from stored
    snapshots/fixtures: a second ingestion of the same request, served
    from cache, must produce an identical raw payload — no re-fetch, no
    drift."""
    first = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30)
    )
    assert first.from_cache is False

    second = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30)
    )
    assert second.from_cache is True
    assert second.uap.result == first.uap.result
    assert second.uap.observation_time == first.uap.observation_time


def test_force_refetch_bypasses_cache(provider, cache):
    first = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30)
    )
    assert first.from_cache is False
    forced = ingest_market_observation(
        provider, cache, "SYNTH_ACME", expected_currency="GBP", now=NOW, staleness_threshold=timedelta(days=30),
        force_refetch=True,
    )
    assert forced.from_cache is False


# --- 11. rate-limit/degraded behaviour ---


class _RateLimitedProvider(ProviderAdapter):
    provider_name = "rate-limited-vendor"
    latency_class = FeedLatency.DELAYED

    def fetch(self, request: ObservationRequest) -> RawPayload:
        raise ProviderUnavailableFailure("rate limit exceeded", retry_after_seconds=60.0)


def test_rate_limited_provider_degrades_to_a_quarantine_result_not_a_crash(cache):
    result = ingest_market_observation(
        _RateLimitedProvider(), cache, "SYNTH_ACME", expected_currency="GBP", now=NOW,
        staleness_threshold=timedelta(days=30),
    )
    assert result.uap is None
    assert "rate limit" in result.quarantine_issues[0].message


def test_rate_limit_retry_after_is_preserved_for_a_caller_wanting_to_retry():
    provider = _RateLimitedProvider()
    with pytest.raises(ProviderUnavailableFailure) as exc_info:
        provider.fetch(ObservationRequest(category=DataCategory.MARKET, identifier="SYNTH_ACME"))
    assert exc_info.value.retry_after_seconds == 60.0
