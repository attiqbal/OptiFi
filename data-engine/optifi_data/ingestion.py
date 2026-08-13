"""
Stage 1 — Data Acquisition orchestration (Phase E2;
`ENGINE_PIPELINE_SPECIFICATION.md` Stage 1): "retrieve raw data from
external and internal sources without transformation... Failed
retrievals must be reported, never silently dropped." This module wires
together `ProviderAdapter` -> `ObservationCache` -> Stage 2 validation
(`validation.py`) -> `UAP`, the full pipeline the task's own diagram
describes ("Provider Adapter -> Canonical OptiFi Observation ->
Validation -> UAP / Data Store").

Duplicate detection lives here (not `validation.py`) because it is
inherently STATEFUL — it needs to know what has already been ingested,
which only this orchestration layer tracks, via an explicit
caller-supplied `previous_uap` (the same "caller supplies the lookup"
convention `check_provenance_resolvable`'s `known_packets` already
established — this module does not own a global store).

Revision/vintage handling: when a newly-ingested record for the same
subject carries a value genuinely different from the previously-ingested
one (a revised release, e.g. CPI advance -> second estimate), this
module calls `optifi_shared.supersede()` rather than overwriting — the
old vintage is preserved, not discarded, per ANALYTICAL_CONTRACT_SPEC.md
Section 5 and this project's own Phase E1 supersession mechanism.

Stage 3 classification rule applied here (`ENGINE_PIPELINE_SPECIFICATION.md`
Stage 3): structured numeric/tabular sources (market prices, official
macro releases) are deterministic parsing and carry
`validation_status=VERIFIED`; events (Category D/E) are treated more
conservatively as `PROVISIONAL` by default, since this project's own
`DATA_SOURCE_REGISTRY.md` names Category D as "the primary source of
PROVISIONAL-status facts" and a "structured" event record does not, on
its own, rule out needing corroboration (a leaked/rumoured guidance
change vs. a confirmed official release, for instance).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from optifi_shared import (
    AnalyticalFailure,
    ConfidenceLevel,
    DuplicateObservationFailure,
    FailureResult,
    InformationClass,
    MacroObservation,
    MarketObservation,
    StructuredEvent,
    supersede,
    UAP,
    ValidationStatus,
)

from .cache import ObservationCache
from .providers import DataCategory, ObservationRequest, ProviderAdapter, ProviderUnavailableFailure, RawPayload
from .validation import validate_macro_observation, validate_market_observation, validate_structured_event

# Task-provided default: market/macro data more than 3 days old is
# treated as stale by default — a DESIGNED calibration placeholder
# (this project's established pattern of naming and justifying such
# constants), not a value any spec document fixes. Callers needing a
# different freshness window pass their own staleness_threshold.
DEFAULT_STALENESS_THRESHOLD = timedelta(days=3)


@dataclass
class IngestionResult:
    """
    The outcome of one ingestion attempt. Exactly one of `uap` or
    `quarantine_issues` is meaningful: a successful ingestion has a real
    `uap` and an empty `quarantine_issues`; a failed one has `uap=None`
    and at least one `FailureResult` explaining why — data failing
    checks is quarantined and flagged, per Stage 2's own rule, never
    silently dropped with no record at all.
    """

    uap: UAP | None
    quarantine_issues: list[FailureResult]
    from_cache: bool
    superseded: UAP | None = None


def _fetch_with_cache(
    provider: ProviderAdapter,
    cache: ObservationCache,
    request: ObservationRequest,
    force_refetch: bool,
) -> tuple[RawPayload | None, list[FailureResult], bool]:
    """Shared fetch-or-cache-hit logic, used by every ingest_* function
    below. Returns (payload_or_None, issues_if_fetch_failed, from_cache)."""
    if not force_refetch:
        cached = cache.get(provider.provider_name, request)
        if cached is not None:
            return cached, [], True

    try:
        payload = provider.fetch(request)
    except ProviderUnavailableFailure as exc:
        return (
            None,
            [
                FailureResult(
                    category="MODEL_FAILURE",
                    message=f"provider '{provider.provider_name}' unavailable: {exc}",
                )
            ],
            False,
        )
    except AnalyticalFailure as exc:
        return None, [FailureResult(category=exc.category, message=str(exc))], False

    cache.put(provider.provider_name, request, payload)
    return payload, [], False


def _parse_observation_time(payload: RawPayload) -> datetime:
    raw = payload.raw_data.get("observation_time")
    parsed = datetime.fromisoformat(raw)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def ingest_market_observation(
    provider: ProviderAdapter,
    cache: ObservationCache,
    instrument_id: str,
    expected_currency: str,
    now: datetime,
    staleness_threshold: timedelta = DEFAULT_STALENESS_THRESHOLD,
    as_of: datetime | None = None,
    previous_price: float | None = None,
    previous_uap: UAP | None = None,
    force_refetch: bool = False,
) -> IngestionResult:
    """Stage 1 + Stage 2, end to end, for a single Category A (market)
    instrument. `previous_uap`, if supplied, is the currently-on-record
    UAP for this exact instrument+observation_time — used only for
    duplicate detection (a genuinely repeated request at the same
    as_of), not for revision handling, which market prices do not
    undergo (a closing price is not later "revised" the way a macro
    release is)."""
    request = ObservationRequest(category=DataCategory.MARKET, identifier=instrument_id, as_of=as_of)
    payload, fetch_issues, from_cache = _fetch_with_cache(provider, cache, request, force_refetch)
    if payload is None:
        return IngestionResult(uap=None, quarantine_issues=fetch_issues, from_cache=from_cache)

    observation, issues = validate_market_observation(
        payload,
        expected_currency=expected_currency,
        now=now,
        staleness_threshold=staleness_threshold,
        previous_price=previous_price,
    )
    if observation is None:
        return IngestionResult(uap=None, quarantine_issues=issues, from_cache=from_cache)

    observation_time = _parse_observation_time(payload)

    if previous_uap is not None and isinstance(previous_uap.result, MarketObservation):
        if previous_uap.observation_time == observation_time:
            if previous_uap.result.price == observation.price:
                return IngestionResult(uap=previous_uap, quarantine_issues=[], from_cache=True)
            return IngestionResult(
                uap=None,
                quarantine_issues=[
                    FailureResult(
                        category=DuplicateObservationFailure.category,
                        message=(
                            f"duplicate observation for {instrument_id} at "
                            f"{observation_time!r}, but with a conflicting "
                            f"value: previously recorded "
                            f"{previous_uap.result.price!r}, newly received "
                            f"{observation.price!r}."
                        ),
                    )
                ],
                from_cache=from_cache,
            )

    uap = UAP(
        subject=f"market price: {instrument_id}",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=observation,
        source=payload.source_identity.publication,
        producer=f"data-engine / {provider.provider_name}",
        confidence=ConfidenceLevel.MODERATE,
        observation_time=observation_time,
        publication_time=observation_time,
        retrieval_time=payload.retrieved_at,
        as_of=as_of,
    )
    return IngestionResult(uap=uap, quarantine_issues=[], from_cache=from_cache)


def ingest_macro_observation(
    provider: ProviderAdapter,
    cache: ObservationCache,
    indicator_name: str,
    now: datetime,
    staleness_threshold: timedelta = DEFAULT_STALENESS_THRESHOLD,
    as_of: datetime | None = None,
    previous_uap: UAP | None = None,
    force_refetch: bool = False,
) -> IngestionResult:
    """
    Stage 1 + Stage 2 for a single Category B (macro) indicator.
    `previous_uap`, if supplied, is the currently-on-record UAP for this
    indicator: if the new observation shares the SAME observation_time
    and value, this is an idempotent duplicate; if it shares the same
    observation_time with a DIFFERENT value, that is a conflict
    (`DuplicateObservationFailure`); if it has a genuinely LATER
    observation_time and a different value, that is treated as a
    REVISION — `previous_uap` is superseded (`supersede()`), not
    overwritten, and returned via `IngestionResult.superseded`.
    """
    request = ObservationRequest(category=DataCategory.MACRO, identifier=indicator_name, as_of=as_of)
    payload, fetch_issues, from_cache = _fetch_with_cache(provider, cache, request, force_refetch)
    if payload is None:
        return IngestionResult(uap=None, quarantine_issues=fetch_issues, from_cache=from_cache)

    observation, issues = validate_macro_observation(payload, now=now, staleness_threshold=staleness_threshold)
    if observation is None:
        return IngestionResult(uap=None, quarantine_issues=issues, from_cache=from_cache)

    observation_time = _parse_observation_time(payload)

    new_uap = UAP(
        subject=f"macro indicator: {indicator_name}",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=observation,
        source=payload.source_identity.publication,
        producer=f"data-engine / {provider.provider_name}",
        confidence=ConfidenceLevel.MODERATE,
        observation_time=observation_time,
        publication_time=observation_time,
        retrieval_time=payload.retrieved_at,
        as_of=as_of,
        vintage=payload.raw_data.get("vintage"),
    )

    if previous_uap is not None and isinstance(previous_uap.result, MacroObservation):
        if previous_uap.observation_time == observation_time:
            if previous_uap.result.value == observation.value:
                return IngestionResult(uap=previous_uap, quarantine_issues=[], from_cache=True)
            return IngestionResult(
                uap=None,
                quarantine_issues=[
                    FailureResult(
                        category=DuplicateObservationFailure.category,
                        message=(
                            f"duplicate observation for {indicator_name} at "
                            f"{observation_time!r}, but with a conflicting "
                            f"value: previously recorded "
                            f"{previous_uap.result.value!r}, newly received "
                            f"{observation.value!r}."
                        ),
                    )
                ],
                from_cache=from_cache,
            )
        if previous_uap.result.value != observation.value:
            new_linked, old_superseded = supersede(previous_uap, new_uap)
            return IngestionResult(uap=new_linked, quarantine_issues=[], from_cache=from_cache, superseded=old_superseded)

    return IngestionResult(uap=new_uap, quarantine_issues=[], from_cache=from_cache)


def ingest_structured_event(
    provider: ProviderAdapter,
    cache: ObservationCache,
    event_identifier: str,
    force_refetch: bool = False,
) -> IngestionResult:
    """Stage 1 + Stage 2 for a single Category D/E (event) record.
    Conservatively PROVISIONAL by default — see module docstring."""
    request = ObservationRequest(category=DataCategory.EVENT, identifier=event_identifier)
    payload, fetch_issues, from_cache = _fetch_with_cache(provider, cache, request, force_refetch)
    if payload is None:
        return IngestionResult(uap=None, quarantine_issues=fetch_issues, from_cache=from_cache)

    observation, issues = validate_structured_event(payload)
    if observation is None:
        return IngestionResult(uap=None, quarantine_issues=issues, from_cache=from_cache)

    observation_time = _parse_observation_time(payload)

    uap = UAP(
        subject=f"structured event: {event_identifier}",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result=observation,
        source=payload.source_identity.publication,
        producer=f"data-engine / {provider.provider_name}",
        confidence=ConfidenceLevel.LOW,
        observation_time=observation_time,
        publication_time=observation_time,
        retrieval_time=payload.retrieved_at,
    )
    return IngestionResult(uap=uap, quarantine_issues=[], from_cache=from_cache)
