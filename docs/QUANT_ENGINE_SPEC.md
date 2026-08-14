# QUANT_ENGINE_SPEC

**Status:** DRAFT (v2.2 — Phase E4, patch: Section 11 item 4 scope clarification)

## 1. Purpose & Scope

This document specifies `quant-engine` in depth: the actual portfolio and
risk methodology it runs, not just its role in the pipeline. This is a
deliberate departure from this project's usual conceptual-only convention —
justified because this domain is standardised financial engineering, not a
contested design choice like causal inference or LLM behaviour. Exact
calibration constants (weights, thresholds) remain open; the methodology
itself does not.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 8. Resolves the
ownership question in `DATA_ARCHITECTURE.md` Section 8 item 3 and
`PRODUCT_VISION.md` Section 18 item 8. Must not violate `AI_ENGINE_SPEC.md`
Section 4 item 4 — `ai-engine` explains this engine's output, never produces
it.

## 3. Boundary Clarification

`quant-engine` computes analytics. It does not execute trades (no
capability in this document connects to any execution surface —
`MVP_ROADMAP.md` Gate C remains closed) and it does not solve the allocation
problem — it supplies `optimisation-engine` (Stage 9) with the statistical
inputs (expected returns, the covariance matrix, risk metrics) that engine
needs to compute candidate allocations. This keeps the eight-engine
separation of concerns intact even as this document adds depth.

## 4. Formal Resolution: `quant-engine` Owns Capital Efficiency Score Computation

Unchanged from the prior draft: `quant-engine` computes the Capital
Efficiency Score and its six sub-scores. This document decides it; three
other documents still need follow-up patches to reflect the decision — see
Section 11.

## 5. Core Methodology Toolkit

### 5.1 Return Calculation
- **Simple return:** `R = (V_end − V_start) / V_start`
- **Log return:** `r = ln(V_end / V_start)`
- **Time-Weighted Return (TWR):** compounds sub-period returns
  geometrically, removing distortion from cash flow timing:
  `TWR = ∏(1 + R_i) − 1`
- **Money-Weighted Return (IRR):** the discount rate that sets the net
  present value of all contributions, withdrawals, and ending value to
  zero. Used where cash-flow timing itself matters to the user (e.g.
  comparing their actual experience to TWR).

### 5.2 Risk-Adjusted Performance Metrics
- **Sharpe Ratio:** `(R_p − R_f) / σ_p` — portfolio return less risk-free
  rate, divided by portfolio standard deviation.
- **Sortino Ratio:** `(R_p − R_f) / σ_d` — as Sharpe, but `σ_d` is downside
  deviation (standard deviation of returns falling below a minimum
  acceptable return), so upside volatility isn't penalised.
- **Treynor Ratio:** `(R_p − R_f) / β_p` — excess return per unit of
  systematic (market) risk rather than total risk.
- **Information Ratio:** `(R_p − R_b) / tracking_error` — active return
  over a benchmark, divided by the standard deviation of that active
  return.
- **Jensen's Alpha (CAPM-based):** `α = R_p − [R_f + β_p(R_m − R_f)]` —
  return in excess of what CAPM predicts given the portfolio's beta.

### 5.3 Risk Measurement
- **Beta:** `β = Cov(R_p, R_m) / Var(R_m)` — sensitivity to market moves.
- **Volatility (annualised):** `σ_annual = σ_period × √(periods per year)`
  (e.g. `× √252` from daily data, `× √12` from monthly).
- **Historical VaR:** the loss at a chosen percentile (e.g. 5th) of the
  portfolio's actual historical return distribution — no distributional
  assumption required.
- **Parametric (variance-covariance) VaR:**
  `VaR = Z_α × σ_p × portfolio_value` — assumes normally distributed
  returns; `Z_α` is the z-score for the chosen confidence level.
- **Conditional VaR / Expected Shortfall:** the average loss in the tail
  beyond the VaR threshold — captures severity, not just the threshold
  itself.
- **Maximum Drawdown:** `MDD = (Trough Value − Peak Value) / Peak Value` —
  largest peak-to-trough decline over the observed period.
- **Downside Deviation:** standard deviation computed only over returns
  falling below a minimum acceptable return (MAR).

### 5.4 Exposure & Concentration Analysis
- **Herfindahl-Hirschman Index (concentration):**
  `HHI = Σ(w_i²) × 10,000`, where `w_i` is the portfolio weight of holding
  `i`. Higher values indicate greater concentration.
- **Weighted exposure sums:** sector/country/currency exposure as the sum
  of position weights within each category.
- **Factor exposure:** tilts toward standard style factors (value, size,
  momentum, quality, low-volatility) — the specific factor model used (e.g.
  a multi-factor regression) is an implementation choice, not fixed here.

### 5.5 Correlation & Covariance
- **Correlation:** `ρ(X,Y) = Cov(X,Y) / (σ_X × σ_Y)`.
- **Portfolio variance (matrix form):** `σ_p² = wᵀ Σ w`, where `w` is the
  vector of position weights and `Σ` is the covariance matrix across
  holdings. **This covariance matrix, plus expected returns per holding, is
  the primary handoff to `optimisation-engine`** (Section 3) — it is not
  computed twice.

## 6. Stage 8 Elaboration — Categories of Output

Applying `ENGINE_PIPELINE_SPECIFICATION.md` Stage 8's existing rule (direct
arithmetic on verified holdings is `FACT`; anything involving a risk or
exposure model is `ESTIMATE`), now grounded in Section 5's formulas:

- **Portfolio analytics** (holdings totals, allocation breakdowns): `FACT`
  where purely arithmetic (Section 5.1's simple/log return on realised
  values).
- **Exposure analysis** (Section 5.4): `ESTIMATE`.
- **Risk measurement** (Section 5.3): `ESTIMATE`.
- **Performance analysis** (Section 5.1/5.2 applied historically): `FACT`
  for realised return on verified transactions; `ESTIMATE` for anything
  forward-looking, benchmark-relative, or model-adjusted (Sharpe, Sortino,
  alpha, beta all use estimated inputs and are `ESTIMATE`).

## 7. The Six Capital Efficiency Sub-Scores — Illustrative Formulas

Each sub-score is `information_class: ESTIMATE`. Formula *structure* is
given; exact weights, bands, and thresholds are explicitly left open for
calibration (Section 11) — no legitimate scoring system ships uncalibrated
constants without real-world tuning, so this isn't a gap unique to this
document.

- **Cash efficiency:**
  `min(100, (achieved_yield_on_cash / best_available_comparable_yield) × 100)`
- **Debt efficiency:** penalised proportionally to the gap between
  effective borrowing cost and the risk-adjusted expected return available
  on capital that could otherwise repay that debt.
- **Risk efficiency:**
  `100 − (|realised_risk − target_risk| / target_risk) × 100`, floored at 0
  — a deviation-from-target-band approach, using the Mandate's stated risk
  tolerance (`DATA_ARCHITECTURE.md` Section 4.1) as the target.
- **Tax efficiency:**
  `(tax_advantaged_allocation_used / tax_advantaged_allocation_available) × 100`
  — utilisation of ISA/pension-style allowances (Tier 1,
  `PRODUCT_VISION.md` Section 6).
- **Liquidity efficiency:** penalised for deviation from the Mandate's
  minimum cash reserve in either direction — whether shortfall and excess
  should be penalised symmetrically or asymmetrically is a calibration
  decision, not fixed here.
- **Investment efficiency:** ratio of the portfolio's achieved Sharpe ratio
  (Section 5.2) to the maximum Sharpe ratio achievable at the same risk
  level on `optimisation-engine`'s efficient frontier for the user's
  Mandate — this makes Investment Efficiency's computation explicitly
  dependent on `optimisation-engine`'s output, which should be reflected in
  this packet's `dependencies` field.

## 8. The Composite Score

Aggregates the six sub-scores — the aggregation method (e.g. a weighted
average, and what those weights are) is left open (Section 11).
`information_class: ESTIMATE`. Per `PRODUCT_VISION.md` Section 11a: `ai-
engine` explains this score, it does not decide it.

## 9. Quantitative Validation (Internal Pre-Check)

Before output reaches `verification-engine` (Stage 11), `quant-engine`
performs its own sanity checks, now concrete given Section 5's formulas:

- The covariance matrix (Section 5.5) must be positive semi-definite —
  otherwise portfolio variance calculations are meaningless.
- VaR and CVaR (Section 5.3) must be non-negative loss magnitudes.
- Any ratio with a volatility denominator (Sharpe, Sortino, Treynor,
  Information Ratio) must guard against a zero or near-zero denominator.
- All portfolio weights (`w_i`) must sum to 1 (or to the invested
  proportion, if cash is held out separately) before being used in Section
  5.4/5.5 calculations.
- Each Capital Efficiency sub-score (Section 7) must fall within its stated
  0–100 bound before the composite score is computed.

## 10. Multi-Signal Disagreement Preservation

Where `quant-engine` computes multiple competing factor signals for the
same target (e.g. a valuation signal positive, a momentum signal negative,
a quality signal positive — Section 5.4), these are preserved as a plural
set sharing one `subject`, per `ANALYTICAL_CONTRACT_SPEC.md` Section 7 — not
collapsed into a single net signal before reaching `ai-engine`.

## 11. Known Gaps / Open Questions

1. Exact weights, bands, and thresholds for each Capital Efficiency
   sub-score (Section 7) and the composite aggregation method (Section 8)
   are deliberately not fixed — calibration against real portfolios and
   real outcomes is a later, empirical step.
2. ~~Three follow-up patches are still needed and not performed here...~~
   **RESOLVED:** all three follow-ups (`DATA_ARCHITECTURE.md` Section 8
   item 3, `PRODUCT_VISION.md` Section 18 items 4 and 8,
   `ENGINE_PIPELINE_SPECIFICATION.md` Section 10's ownership table)
   landed in the batch patch that immediately followed this document's
   creation.
3. Whether Liquidity Efficiency's shortfall/excess penalty is symmetric or
   asymmetric (Section 7) is unresolved.
4. Which specific factor model (Section 5.4) `quant-engine` uses for factor
   exposure is not chosen here — only that the category of output exists.
   **Not resolved by Phase E4:** that phase's `factor_sensitivity.py`
   implements sensitivity to a single, NAMED macro/market driver (a
   yield, a rate, an FX pair) for scenario-transmission purposes
   (`PHASE E4` brief) — a genuinely different axis of "factor" than this
   item's equity STYLE-factor model (value, size, momentum, quality,
   low-volatility). Conflating the two would misrepresent Phase E4 as
   having resolved this item; it did not touch it.
5. Historical vs. parametric vs. Monte Carlo VaR (Section 5.3) — this
   document specifies all three as available methods; which is used by
   default, or whether all three are computed and reconciled, is not
   decided.
