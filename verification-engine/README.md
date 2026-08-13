# verification-engine

Stage 11: independent verification (`VERIFICATION_FRAMEWORK.md`) —
checks candidates and their supporting facts/estimates/judgements *at
decision time*. Distinct from `evaluation-engine` (Stage 14), which
tracks realised outcomes and model/recommendation performance *after
the fact, over time*.

**Implemented:**
- The four-verdict taxonomy (PASS / PASS WITH CAUTION / FLAG / REJECT)
  and its effect on `validation_status`
- Independent re-derivation of optimisation-engine candidates,
  including loss-cap and hedging-structure (protective put / collar)
  checks
- An independent corroboration audit and a check that `ai-engine`'s
  candidate framing hasn't altered the underlying figures
- Provenance-chain resolvability and look-ahead-contamination checks
- 58 automated tests

**Not yet implemented:**
- Verification coverage for every specialist engine's output — this
  package checks optimisation, hedging, corroboration, framing, and
  time/provenance integrity specifically, not a general-purpose
  verifier for arbitrary output
- A meta-verification mechanism ("who verifies the verifier" — an open
  question in `VERIFICATION_FRAMEWORK.md`)
