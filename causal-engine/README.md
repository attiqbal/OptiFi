# causal-engine

Stage 5: causal analysis (`CAUSAL_ENGINE_SPEC.md`).

**Implemented:**
- `CausalClaim`, the structural contract every causal claim must
  satisfy, including a guardrail against presenting correlation as
  causation
- One illustrative example (UK base-rate cut → mortgage refinancing
  rate)
- 9 automated tests

**Not yet implemented:**
- Any actual causal-inference methodology — `CAUSAL_ENGINE_SPEC.md`
  Section 3 deliberately leaves this undecided
