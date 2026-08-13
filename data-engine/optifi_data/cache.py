"""
Local, deterministic ingestion cache — Phase E2. "External data must not
need to be repeatedly downloaded during tests... Historical tests must
be reproducible from stored snapshots/fixtures." This is a simple,
file-backed (JSON) cache keyed by (provider, category, identifier,
as_of) — swappable for a real persistence layer later without changing
callers; `ingestion.py` only depends on this module's own three-method
interface (`get`/`put`/`clear`), never on the storage format directly.

This is a CACHE, not a source of truth: a cached `RawPayload` still
carries its own original `retrieved_at`/`source_identity` from when it
was actually fetched — reading from cache never fabricates a new
retrieval event or backdates/updates that metadata.
"""

from __future__ import annotations

from pathlib import Path

from .providers import ObservationRequest, RawPayload


def _cache_key(provider_name: str, request: ObservationRequest) -> str:
    as_of_part = request.as_of.isoformat() if request.as_of else "latest"
    # Filesystem-safe: no colons (Windows-hostile) or slashes.
    safe_as_of = as_of_part.replace(":", "-")
    return f"{provider_name}__{request.category.value}__{request.identifier}__{safe_as_of}"


class ObservationCache:
    """
    A directory of one JSON file per cached `RawPayload`, keyed by
    provider + request. `get` returns `None` on a cache miss (never
    fabricates a payload); `put` always overwrites (a cache is allowed
    to be refreshed) — but see `ingestion.py` for how the ingestion
    pipeline itself decides whether re-fetching is warranted; this class
    has no opinion on that policy.
    """

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, provider_name: str, request: ObservationRequest) -> Path:
        return self.cache_dir / f"{_cache_key(provider_name, request)}.json"

    def get(self, provider_name: str, request: ObservationRequest) -> RawPayload | None:
        path = self._path_for(provider_name, request)
        if not path.exists():
            return None
        return RawPayload.model_validate_json(path.read_text())

    def put(self, provider_name: str, request: ObservationRequest, payload: RawPayload) -> None:
        path = self._path_for(provider_name, request)
        path.write_text(payload.model_dump_json())

    def clear(self) -> None:
        for cached_file in self.cache_dir.glob("*.json"):
            cached_file.unlink()
