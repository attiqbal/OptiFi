# ai-engine

Stages 3 (unstructured support), 10, 12, 13: candidate framing,
disagreement-preserving synthesis, and disclosure (`AI_ENGINE_SPEC.md`).

**Implemented:**
- Candidate framing (Stage 10) that cannot alter the underlying figures
  it explains
- Disagreement grouping and disagreement-preserving synthesis (Stage
  12) — the CIO layer is not permitted to mathematically resolve
  disagreement between competing model outputs, and cannot here even if
  it tried
- Non-`VERIFIED` disclosure logic (Stage 13) — a caveat is never
  silently dropped
- Structured-claim extraction (Stage 3 unstructured-text support)
- 42 automated tests

**Not yet implemented:**
- Any real LLM provider integration — every function here takes an
  `ExplanationGenerator`, and the only implementation is
  `StubExplanationGenerator`; no API key, network call, or real model
  is used anywhere in this package
- Full recommendation generation or live CIO synthesis
