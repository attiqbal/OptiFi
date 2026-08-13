# quant-engine

Stage 8: portfolio and risk analytics (`QUANT_ENGINE_SPEC.md`).

**Implemented:**
- Sharpe ratio, historical and parametric Value-at-Risk
- Covariance/correlation matrices and portfolio variance, with
  independent symmetry/positive-semi-definite validation
- The Capital Efficiency Score (six sub-scores plus composite)
- Minimum-variance hedge ratio
- 82 automated tests

**Not yet implemented:**
- Other risk-adjusted return ratios, exposure/concentration metrics,
  and the remaining `QUANT_ENGINE_SPEC.md` Section 5 metrics beyond the
  above
- Basis-risk disclosure and dynamic hedge rebalancing
  (`HEDGING_SPEC.md`)
