# data-engine

Stage 1–2 of the pipeline: data acquisition and validation
(`ENGINE_PIPELINE_SPECIFICATION.md`).

**Implemented:**
- Corroboration mechanism for upgrading a `PROVISIONAL` fact to
  `VERIFIED` (`ANALYTICAL_CONTRACT_SPEC.md` Section 4a)
- A provider-agnostic `ProviderAdapter` interface, with a deterministic
  `FixtureProvider` as the only implementation
- Stage 1 acquisition and Stage 2 validation orchestration: staleness,
  duplicate, currency-mismatch, discontinuity, and calendar-mismatch
  checks
- Revision/vintage handling (superseding an earlier release rather than
  overwriting it) and a local cache for byte-for-byte deterministic
  replay
- Canonical asset identity resolution
- 71 automated tests

**Not yet implemented:**
- Any real, live, or paid market/macro/fundamentals data vendor —
  every adapter beyond `FixtureProvider` remains unbuilt; see
  `docs/DATA_SOURCE_REGISTRY.md` for the (unresolved) vendor evaluation
