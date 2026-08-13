# optimisation-engine

Stages 9a/9b: candidate generation and constraint validation
(`OPTIMISATION_ENGINE_SPEC.md`).

**Implemented:**
- Mean-variance minimisation, with and without a mandate single-period
  loss cap enforced as a solver constraint
- Maximum-Sharpe (tangency) portfolio and the efficient frontier
- Two defined-risk options structures: protective put and collar
  (`HEDGING_SPEC.md` Section 5)
- Independent boundary validation (covariance symmetry/PSD
  re-verification) rather than trusting an upstream matrix
- 75 automated tests

**Not yet implemented:**
- The full mandate constraint taxonomy (tax, ESG, liquidity, exclusions
  beyond generic per-asset weight bounds and the loss cap) and Section
  8's policy gate-checking
