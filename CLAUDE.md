# CLAUDE.md

OptiFi has moved past initial scaffolding. Nine specialist engines
(`data-engine`, `causal-engine`, `quant-engine`, `forecast-engine`,
`evaluation-engine`, `simulation-engine`, `optimisation-engine`,
`ai-engine`, `verification-engine`) plus `shared` contain real,
tested implementation — see `README.md` for an accurate breakdown of
what is implemented, experimental, synthetic-only, or still deferred.
`backend`, `frontend`, `infrastructure`, `research`, and `scripts`
remain placeholders.

This does not change the working rules below, which remain in force
for all future work in this repository:

* Claude must not silently invent or resolve architecture, product,
  regulatory, or financial-model decisions. Where a genuinely material
  decision is unresolved, document the issue, the available options,
  and their trade-offs, and stop before making an irreversible choice
  — see `/docs` for the project's own precedent of doing this (each
  spec's "Known Gaps / Open Questions" section).
* Preserve the existing architecture — the Universal Analytical Packet
  contract, the FACT/ESTIMATE/JUDGEMENT and validation-status
  distinctions, and each engine's documented ownership boundary
  (`ENGINE_PIPELINE_SPECIFICATION.md` Section 10) — unless a task
  explicitly authorises a change, and document any change made.
* No real user bank/brokerage accounts, no trade execution, and no
  personalised live investment execution. Data ingestion currently
  runs only against a deterministic fixture provider; connecting a
  real vendor is a deliberate, separate, not-yet-made decision (see
  `docs/DATA_SOURCE_REGISTRY.md`).
* Never fabricate unavailable financial information, never convert
  model agreement into certainty, and never remove uncertainty merely
  to simplify downstream output.
* Every new analytical behaviour needs automated tests, including a
  negative/adversarial test for every "must never happen" rule it
  introduces.

This file will continue to evolve as the permanent Claude Code
project-instructions document as OptiFi's implementation grows.
