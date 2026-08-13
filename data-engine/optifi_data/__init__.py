"""
optifi_data — data-engine.

Implements the corroboration mechanism (ANALYTICAL_CONTRACT_SPEC.md
Section 4a) — pure logic operating on UAP objects — and, since Phase E2,
real-data ingestion infrastructure: canonical asset identity, a
provider-agnostic adapter abstraction, a deterministic fixture-backed
reference provider, Stage 1 acquisition orchestration, Stage 2
validation/data-quality checks, and a local reproducibility cache. No
live external vendor is connected — see the Phase E2 deliverable's
Source Selection section.
"""

from .asset_identity import AssetIdentity, asset_identity_conflicts, AssetType
from .cache import ObservationCache
from .corroboration import corroborate_fact
from .ingestion import (
    DEFAULT_STALENESS_THRESHOLD,
    ingest_macro_observation,
    ingest_market_observation,
    ingest_structured_event,
    IngestionResult,
)
from .providers import (
    DataCategory,
    FeedLatency,
    FixtureProvider,
    ObservationRequest,
    ProviderAdapter,
    ProviderUnavailableFailure,
    RawPayload,
)

__all__ = [
    "corroborate_fact",
    "AssetIdentity",
    "AssetType",
    "asset_identity_conflicts",
    "DataCategory",
    "FeedLatency",
    "ObservationRequest",
    "RawPayload",
    "ProviderAdapter",
    "ProviderUnavailableFailure",
    "FixtureProvider",
    "ObservationCache",
    "IngestionResult",
    "DEFAULT_STALENESS_THRESHOLD",
    "ingest_market_observation",
    "ingest_macro_observation",
    "ingest_structured_event",
]
