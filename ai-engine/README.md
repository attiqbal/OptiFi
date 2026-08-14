# ai-engine

Stages 3 (unstructured support), 10, 12, 13: candidate framing,
disagreement-preserving synthesis, disclosure, and CIO/Manager
orchestration (`AI_ENGINE_SPEC.md`, `docs/CIO_ORCHESTRATION_SPEC.md`).

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
- CIO orchestration (Phase E6): dynamic routing (`intent.py`), roadblock
  detection (`roadblock.py`), a verification-gate mapping that can never
  override a REJECT verdict (`verification_gate.py`), a "Why?" evidence
  trace (`evidence_trace.py`), sophistication-tiered explanation
  (`explanation.py`), and an orchestrator tying it together
  (`orchestrator.py`) with two real, fully-worked routing examples
- 90 automated tests, including 11 adversarial tests targeting prompt
  injection, disagreement, staleness, rejected verification, and
  missing/unsupported assets

**Not yet implemented:**
- Any real LLM provider integration — every function here takes an
  `ExplanationGenerator`, and the only implementation is
  `StubExplanationGenerator`; no API key, network call, or real model
  is used anywhere in this package
- Real NLU-based intent classification — routing is a documented
  keyword heuristic (`intent.py`), not genuine language understanding
- A live `backend` service layer that dispatches to specialist engines
  over the network at runtime — the CIO reasons over an
  already-populated `SpecialistOutputPool`; every specialist "call" in
  this package's tests is a direct, in-process function call
