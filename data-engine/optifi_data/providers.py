"""
Provider abstraction — Phase E2. "Provider Adapter -> Canonical OptiFi
Observation -> Validation -> UAP / Data Store." The rest of OptiFi never
depends on which external provider produced a given observation — every
adapter, real or fixture-backed, implements the exact same interface and
returns the exact same raw shape (`RawPayload`); everything downstream of
`ProviderAdapter.fetch` is provider-agnostic.

No real external vendor is connected anywhere in this module.
`DATA_SOURCE_REGISTRY.md` Section 6 item 1 explicitly defers "actual
vendor and licensing decisions... a procurement decision" out of scope
for that document, and this phase does not silently resolve it either —
see the Phase E2 deliverable's Source Selection section for the
evaluated, real-world candidate vendors and why none was connected.

`FixtureProvider` below is a REAL, fully working `ProviderAdapter` — not
a placeholder — it reads from local, checked-in JSON fixture files
instead of a network call. This directly satisfies the task's own
"Historical tests must be reproducible from stored snapshots/fixtures"
requirement, and proves the full pipeline end to end without needing API
keys, cost, or a live network dependency. Its fixture data is
SYNTHETIC/ILLUSTRATIVE, clearly labelled as such throughout (matching
this project's own established precedent for synthetic test data,
quant-engine's `synthetic_realistic_daily_returns`) — never presented
as, or usable as, real market/economic history.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from optifi_shared import MissingInputFailure, SourceIdentity


class FeedLatency(str, Enum):
    """
    How fresh a feed genuinely is. Phase E2's own explicit requirement:
    "Do not claim something is 'real time' unless the source genuinely
    supports that latency." A provider adapter must declare one of
    these explicitly; nothing here defaults to `REAL_TIME`.
    """

    REAL_TIME = "REAL_TIME"
    DELAYED = "DELAYED"
    END_OF_DAY = "END_OF_DAY"
    PERIODIC_RELEASE = "PERIODIC_RELEASE"
    HISTORICAL_ONLY = "HISTORICAL_ONLY"


class DataCategory(str, Enum):
    """DATA_SOURCE_REGISTRY.md's own Category A-D, as a controlled
    taxonomy (Category E/F are out of this phase's MVP scope — see the
    Phase E2 deliverable's deferred-categories section)."""

    MARKET = "MARKET"
    MACRO = "MACRO"
    FUNDAMENTAL = "FUNDAMENTAL"
    EVENT = "EVENT"


class ObservationRequest(BaseModel):
    """
    What a caller asks a provider for. `identifier`'s meaning is
    category-dependent: an instrument identifier for `MARKET`, an
    indicator name for `MACRO`, an "issuer/metric" identifier for
    `FUNDAMENTAL`, an event-type identifier for `EVENT`.
    """

    category: DataCategory
    identifier: str
    as_of: datetime | None = Field(
        default=None, description="Point-in-time request; None means 'latest available'."
    )


class RawPayload(BaseModel):
    """
    Stage 1 output (`ENGINE_PIPELINE_SPECIFICATION.md`): raw,
    unclassified data with source and retrieval-timestamp metadata —
    not yet validated or normalised (that is Stage 2, see
    `validation.py`).
    """

    raw_data: dict
    provider_name: str
    source_identity: SourceIdentity
    latency_class: FeedLatency
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProviderUnavailableFailure(Exception):
    """
    Raised when a provider adapter cannot currently be reached at all
    (rate limit, network error, outage) — distinct from
    `optifi_shared.AnalyticalFailure`, which describes a problem with
    the DATA itself (missing, stale, conflicting). This describes a
    problem reaching the source, potentially transient, which callers
    may reasonably want to handle differently (e.g. retry with backoff)
    from a genuine analytical failure.
    """

    def __init__(self, message: str, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ProviderAdapter(ABC):
    """
    Every provider adapter — real or fixture-backed — implements this
    same interface. Downstream code depends ONLY on this interface,
    never on any specific provider's own API shape: swapping
    `FixtureProvider` for a real vendor adapter later requires zero
    changes to the ingestion pipeline, validation, or any analytical
    engine.
    """

    provider_name: str
    latency_class: FeedLatency

    @abstractmethod
    def fetch(self, request: ObservationRequest) -> RawPayload:
        """
        Retrieve raw data for `request`. Must raise
        `ProviderUnavailableFailure` if the source cannot currently be
        reached, or an `optifi_shared.AnalyticalFailure` subclass
        (typically `MissingInputFailure`) if the source is reachable
        but has no data for this request — never return a fabricated or
        partial result, per this project's founding rule against
        fabricating unavailable financial information.
        """
        raise NotImplementedError


class FixtureProvider(ProviderAdapter):
    """
    A REAL, working `ProviderAdapter` reading from local, checked-in
    JSON fixture files — the deterministic/offline half of this system
    (task: "Historical tests must be reproducible from stored
    snapshots/fixtures... Live ingestion tests should be clearly
    separated from deterministic offline tests"). No live vendor is
    connected; see the module docstring.

    Fixture files live under
    `<fixture_dir>/<category>/<identifier>.json` — a JSON list of raw
    observation records, oldest first. Each record must carry its own
    `observation_time` (ISO 8601) and `source_identity` (a
    `SourceIdentity`-shaped dict). SYNTHETIC data only — see the module
    docstring's warning; nothing here should be read as, or presented
    as, real market/economic history.
    """

    def __init__(
        self,
        fixture_dir: Path,
        provider_name: str = "fixture-provider",
        latency_class: FeedLatency = FeedLatency.HISTORICAL_ONLY,
        fixed_retrieved_at: datetime | None = None,
    ) -> None:
        self.fixture_dir = Path(fixture_dir)
        self.provider_name = provider_name
        self.latency_class = latency_class
        # Deterministic by default -- NOT real wall-clock time. A
        # fixture-backed provider exists specifically for reproducible
        # offline tests ("Historical tests must be reproducible from
        # stored snapshots/fixtures"); tying its retrieved_at to actual
        # datetime.now() would make that reproducibility depend on
        # which real calendar day the test suite happens to run on --
        # every fixture's own observation_time must stay safely BEFORE
        # this constant for the timestamp-consistency check
        # (validation.py) to hold indefinitely, not just today.
        self.fixed_retrieved_at = fixed_retrieved_at or datetime(2099, 1, 1, tzinfo=timezone.utc)

    def fetch(self, request: ObservationRequest) -> RawPayload:
        fixture_path = self.fixture_dir / request.category.value.lower() / f"{request.identifier}.json"
        if not fixture_path.exists():
            raise MissingInputFailure(
                f"FixtureProvider: no fixture found for "
                f"{request.category.value}/{request.identifier} at "
                f"{fixture_path} — nothing fabricated in its place."
            )
        with fixture_path.open() as f:
            records = json.load(f)
        if not records:
            raise MissingInputFailure(
                f"FixtureProvider: fixture for "
                f"{request.category.value}/{request.identifier} exists "
                "but contains no records."
            )

        record = self._select_record(records, request)
        if record is None:
            raise MissingInputFailure(
                f"FixtureProvider: no record for "
                f"{request.category.value}/{request.identifier} at "
                f"as_of={request.as_of!r}."
            )

        return RawPayload(
            raw_data=record,
            provider_name=self.provider_name,
            source_identity=SourceIdentity(**record["source_identity"]),
            latency_class=self.latency_class,
            retrieved_at=self.fixed_retrieved_at,
        )

    @staticmethod
    def _select_record(records: list[dict], request: ObservationRequest) -> dict | None:
        if request.as_of is None:
            return records[-1]  # "latest available" -- fixtures are stored oldest-first
        for record in records:
            record_time = datetime.fromisoformat(record["observation_time"])
            if record_time.tzinfo is None:
                record_time = record_time.replace(tzinfo=timezone.utc)
            if record_time == request.as_of:
                return record
        return None
