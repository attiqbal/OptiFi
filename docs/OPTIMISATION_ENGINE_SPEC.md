# OPTIMISATION_ENGINE_SPEC

**Status:** DRAFT (v1.2 — Phase 9, patch: loss cap documented, Section 10 item 1 resolved)

## 1. Purpose & Scope

This document specifies `optimisation-engine`: what it computes at Stages
9a and 9b, its mathematical methodology, and its constraint model. This
document has never existed before — its absence was flagged as a known gap
back in Phase 0 and left unaddressed while two other documents
(`AI_ENGINE_SPEC.md`, `VERIFICATION_FRAMEWORK.md`) went on to write hard
constraints against behavior this document had never defined.

## 2. Relationship to Prior Documents

Consumes `QUANT_ENGINE_SPEC.md` Section 5.5's covariance matrix and
expected-returns handoff directly — that document explicitly names this
engine as the recipient. Constrained by `DATA_ARCHITECTURE.md` Section 4.1
(the Mandate) and `MVP_ROADMAP.md`'s gates. Its output is what
`AI_ENGINE_SPEC.md` Section 3.2 forbids `ai-engine` from altering, and what
`VERIFICATION_FRAMEWORK.md` Section 5.5 independently re-checks. Feeds back
into `QUANT_ENGINE_SPEC.md` Section 7's Investment Efficiency sub-score via
the efficient frontier (Section 5.3 below).

## 3. Boundary Clarification

`optimisation-engine` solves the allocation problem given the statistical
inputs `quant-engine` supplies — it does not compute those inputs itself
(covariance, expected returns), and it does not execute anything. No
capability in this document connects to an execution surface.

## 4. Formal Resolution: `optimisation-engine` Owns Both Stage 9a and Stage 9b

`ENGINE_PIPELINE_SPECIFICATION.md` left Stage 9b's ownership as "pending
confirmation." **Resolved here: `optimisation-engine` owns both Stage 9a
(candidate generation) and Stage 9b (policy/constraint validation)** — Stage
9b is this engine's own self-check on what it just generated, distinct from
`verification-engine`'s independent re-check at Stage 11. A follow-up patch
to `ENGINE_PIPELINE_SPECIFICATION.md` Section 10 (removing "pending
confirmation") and Section 12 is needed and not performed in this task —
see Section 10.

## 5. Core Methodology: Mean-Variance Optimisation

### 5.1 The Optimisation Problem
Given the covariance matrix `Σ` and expected-returns vector `μ` from
`quant-engine`, the classical (Markowitz) formulation:

**Minimise:** `σ_p² = wᵀ Σ w` (portfolio variance)
**Subject to:** `wᵀ μ = R_target`, `Σ w_i = 1`, plus the Mandate's
constraint set (Section 6).

Solved across a range of `R_target` values, this traces the efficient
frontier (Section 5.3).

### 5.1a Loss-Capped Variant

Implemented as `minimize_variance_with_loss_cap`, alongside the base
Section 5.1 solver. Adds one constraint to the same convex problem:

`Z_α × √(wᵀΣw) × portfolio_value ≤ max_single_period_loss`

where `Z_α` is derived from a stated confidence level (typically 95%)
via the same approach `quant-engine`'s `parametric_var` uses. This
caps the portfolio's single-period Value-at-Risk directly inside the
solver — a candidate that would breach the cap is infeasible to
produce, not generated and then flagged. This is distinct from the
Mandate's "maximum acceptable drawdown" (a multi-period, peak-to-trough
notion) — see Section 6 below for how it fits the constraint taxonomy,
and `DATA_ARCHITECTURE.md` Section 4.1 for the Mandate parameter this
draws from.

### 5.2 Maximum Sharpe Ratio (Tangency Portfolio)
An alternative objective, useful when no specific target return is
supplied:

**Maximise:** `(wᵀ μ − R_f) / √(wᵀ Σ w)`

subject to the same constraint set.

### 5.3 The Efficient Frontier
The set of portfolios solving Section 5.1 across varying `R_target` —
tracing achievable risk/return combinations. **This is the direct input to
`QUANT_ENGINE_SPEC.md` Section 7's Investment Efficiency sub-score**, which
compares the portfolio's achieved Sharpe ratio to the maximum achievable
Sharpe ratio at the same risk level on this frontier. This engine computing
the frontier is what makes that sub-score computable at all.

## 6. Constraint Taxonomy

- **Hard constraints** — must never be violated: leverage prohibition (if
  set), hard exclusions, maximum individual-position and sector-allocation
  limits, crypto ceiling, minimum cash reserve, a maximum single-period
  loss (VaR-based, per Section 5.1a), sourced from the Mandate's
  `max_single_period_loss` parameter — all from the Mandate
  (`DATA_ARCHITECTURE.md` Section 4.1). Violation → automatic `REJECT` in
  Stage 9b.
- **Soft constraints / preferences** — e.g. ESG preferences. Violation →
  deprioritise or `FLAG`, not automatic rejection. Exact treatment is open
  (Section 10).
- **Regulatory / gate constraints** — no candidate may be generated at all
  that would require a currently-closed gate (`MVP_ROADMAP.md` Gate B, Gate
  C). This is checked at generation time, not filtered out afterward — see
  Section 8.

## 7. Stage 9a — Candidate Generation

Given the current portfolio and a target point on the efficient frontier (or
a specific identified inefficiency, e.g. idle cash), `optimisation-engine`
computes the delta between current and target allocation. This delta,
expressed as a specific action with its quantitative impact, is the
candidate: `{action description, expected_risk_change,
expected_return_change, constraint_check_results}`. `information_class:
ESTIMATE`. Output must expose the constraint set and objective assumptions
used (`ENGINE_PIPELINE_SPECIFICATION.md`, Stage 9a) — not the numerical
method itself. `dependencies` must reference the specific `quant-engine`
UAP(s) (covariance matrix, expected returns) the candidate was computed
from.

## 8. Stage 9b — Policy / Constraint Validation

`optimisation-engine`'s own self-check on candidates it just generated,
before they reach `ai-engine` (Stage 10):

1. Every hard constraint (Section 6) is checked; a violation marks the
   candidate `REJECTED` and excludes it from what reaches Stage 10.
2. **Gate status is checked at generation time** — a candidate that would
   require Gate B (personalised trust/charity structuring) or Gate C
   (execution) cannot be generated at all while that gate is closed. This
   is defense-in-depth: it means a gated action can't even exist as a
   candidate, rather than relying solely on `ai-engine` to refrain from
   framing it or `verification-engine` to catch it downstream.
3. This is `optimisation-engine`'s own first-pass check, distinct from and
   not a substitute for `verification-engine`'s independent Stage 11
   re-check (`VERIFICATION_FRAMEWORK.md`, Section 5.5) — consistent with
   the same internal-check-vs-independent-check distinction already
   established in `QUANT_ENGINE_SPEC.md` Section 9.

## 9. Multi-Candidate Handling

`optimisation-engine` may generate more than one candidate for the same
identified inefficiency (e.g. different points on the efficient frontier).
**This is not the same thing as multi-model disagreement**
(`ANALYTICAL_CONTRACT_SPEC.md` Section 7) — these are legitimate alternative
options answering the same question the same way, not competing models
disagreeing about one answer. `ai-engine` (Stage 10) may rank and compare
them, consistent with its existing permission to do so
(`AI_ENGINE_SPEC.md`, Section 3.2).

## 10. Known Gaps / Open Questions

1. ~~The exact numerical optimisation method...~~ **RESOLVED:** both
   `minimize_variance` and `minimize_variance_with_loss_cap` use `cvxpy`
   to solve a convex quadratic program — the example this item itself
   named.
2. Whether a soft/ESG constraint violation should `FLAG` a candidate or
   merely deprioritise it (Section 6) is not decided.
3. How ties between multiple equally-optimal candidates (Section 9) are
   selected or ordered before reaching `ai-engine` is not decided.
4. ~~A follow-up patch to `ENGINE_PIPELINE_SPECIFICATION.md` is
   needed...~~ **RESOLVED:** that patch was completed — Section 10's
   table no longer says "pending confirmation," and Section 12's Stage 9b
   item is marked resolved, citing this document's Section 4. A later
   patch also corrected two further stale references to the same fact in
   that document's Sections 8 and 9.
5. The exact confidence level used for the loss cap's VaR calculation
   (typically 95% in examples so far) is not fixed as a default —
   calibration against real use remains open, consistent with
   `QUANT_ENGINE_SPEC.md`'s existing calibration deferrals.
