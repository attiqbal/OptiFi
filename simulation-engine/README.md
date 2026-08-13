# simulation-engine

Stage 7: scenario generation and simulation
(`SIMULATION_ENGINE_SPEC.md`).

**Implemented:**
- `ScenarioResult`, the structural contract every scenario output must
  satisfy, with a mandatory uncertainty-range guardrail
- One illustrative example (a UK base-rate-cut scenario)
- 11 automated tests

**Not yet implemented:**
- Any actual scenario-propagation or Monte Carlo algorithm — Section 6
  of `SIMULATION_ENGINE_SPEC.md` is deliberately left
  methodology-agnostic and unimplemented
