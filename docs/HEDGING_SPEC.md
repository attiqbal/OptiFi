# HEDGING_SPEC

**Status:** DRAFT (v1 — Phase 15)

## 1. Purpose & Scope

This document specifies OptiFi's first hedging and options-based risk
management capability. Scope is deliberately narrow for this version:

**In scope:**
- Hedge ratio calculation (Section 4) — the minimum-variance hedge ratio,
  cross-hedging/basis risk, and dynamic hedging as an open question.
- Two defined-risk options structures only (Section 5): the **protective
  put** and the **collar**.

**Explicitly excluded from this version, named as future scope, not
silently omitted:**
- **Covered calls as a standalone strategy.** Note the distinction from
  the collar: the collar (in scope) is a two-leg structure whose call leg
  is a covered call *by construction*, since it is written against the
  same already-held underlying position within that single structure. This
  document does not support writing a covered call as its own independent
  strategy, separate from a collar. That is future scope.
- **Delta hedging** (and Greeks-driven dynamic rebalancing generally,
  beyond the open rebalancing-cadence question in Section 4.3).
- **Any multi-leg or exotic structure** beyond the two-leg collar —
  straddles, strangles, spreads, iron condors, ratio spreads, or anything
  else. Future scope.

Consistent with every other engine spec in this project, this document
specifies risk-management *methodology and structure*, not execution. See
Section 3.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 8 (portfolio/user
impact analysis) and Stage 9a (candidate generation) into a new capability
neither stage's original text anticipated. Reuses `QUANT_ENGINE_SPEC.md`
Section 5.5's covariance/variance/correlation machinery directly (Section
4.1 below) rather than introducing parallel statistics. Extends
`OPTIMISATION_ENGINE_SPEC.md` Section 6's constraint taxonomy (Section 8
below) and follows its Section 5.1a loss-cap precedent directly (Section 6
below) — this is the most load-bearing cross-reference in this document.
Constrained by the same Mandate (`DATA_ARCHITECTURE.md` Section 4.1) and
the same `MVP_ROADMAP.md` gates as every other engine. Does not resolve
engine ownership (Section 7) — that remains a proposal pending formal
confirmation, unlike `QUANT_ENGINE_SPEC.md` Section 4's resolved Capital
Efficiency Score ownership.

## 3. Boundary Clarification

This document specifies how to calculate a hedge ratio and how to
structure a defined-risk options position. It does not execute anything —
no capability in this document connects to an execution surface
(`MVP_ROADMAP.md` Gate C remains closed), consistent with every other
engine's boundary (`OPTIMISATION_ENGINE_SPEC.md` Section 3,
`QUANT_ENGINE_SPEC.md` Section 3). Whether options-based recommendations
carry any *additional* regulatory constraint beyond Gate C's existing
advice-vs-guidance question is not addressed here — see Section 9, item 4.

## 4. Hedging Methodology

### 4.1 Minimum-Variance Hedge Ratio

Given a held position (or exposure) `S` and a candidate hedging instrument
`F`, the minimum-variance hedge ratio is:

`h* = Cov(ΔS, ΔF) / Var(ΔF) = ρ(ΔS, ΔF) × (σ_S / σ_F)`

where `ΔS`/`ΔF` are period changes in the value of the position and the
hedging instrument, and `ρ`, `σ_S`, `σ_F` are their correlation and
standard deviations. `h*` minimizes `Var(ΔS − h × ΔF)` — the variance of
the *hedged* position's value change — over choices of `h`.

This is structurally the same formula as `QUANT_ENGINE_SPEC.md` Section
5.3's Beta (`β = Cov(R_p, R_m) / Var(R_m)`), and reuses the same
building blocks Section 5.5 already defines (`covariance_matrix`,
`portfolio_variance`, correlation) — no new statistical methodology is
introduced by hedge ratio calculation itself, only a new application of
existing ones. See Section 7 for which engine should own this.

**Hedge effectiveness** is assessed via `R² = ρ(ΔS, ΔF)²` — the fraction
of the position's own variance eliminated by the hedge. `R² = 1` implies a
perfect hedge (impossible in practice for anything but an identical
instrument); `R² = 0` implies the hedge instrument does nothing for this
exposure. Whether any minimum `R²` should be required before a hedge is
recommended at all is not decided — see Section 9, item 7.

### 4.2 Cross-Hedging and Basis Risk

A **cross-hedge** exists when no instrument perfectly matching the held
exposure is available (the common case — e.g. hedging a specific
single-name equity position with an index future, or a specific-duration
bond exposure with a different-duration instrument). `h*` still minimizes
variance, but cannot eliminate it: residual variance after hedging is
`(1 − R²) × Var(ΔS)` — this is **basis risk**, the risk that the position
and the hedge instrument's prices don't move in lockstep. Whether this
residual should be surfaced as its own explicit field on a hedge
recommendation's `UAP` (`ANALYTICAL_CONTRACT_SPEC.md` Section 5's
`assumptions`/`limitations`) is not specified in enough detail to be
considered decided here — see Section 9, item 8.

### 4.3 Dynamic Hedging — Genuinely Open, Not Resolved Here

A computed `h*` is estimated from historical covariance/variance over some
lookback window. As market conditions change — correlation between the
position and hedge instrument drifts, volatility regimes shift — `h*`
decays in accuracy and the hedge needs periodic re-estimation and
rebalancing. **This document deliberately does not invent an answer for
what triggers a rebalance.** Two genuinely open questions, left open:

1. **Cadence.** Calendar-based (e.g. monthly, quarterly), threshold-based
   (e.g. rebalance when realised correlation drifts beyond some stated
   band), or some combination — not decided.
2. **Trigger.** Whether rebalancing is scheduled, event-triggered (a
   volatility regime change, a large move in the underlying), or
   user-initiated — not decided.

Consistent with this project's established pattern
(`QUANT_ENGINE_SPEC.md` Section 11, item 1: exact calibration constants
are deliberately deferred to real-use calibration), this is named as an
open question rather than resolved by an invented default.

## 5. Options-Based Risk Coverage (Defined-Risk Structures Only)

Both structures below share one property central to Section 6: their
maximum possible loss is finite and computable *before* the structure is
ever generated, from the structure's own inputs alone. Nothing in this
section requires trusting a downstream check to catch an unbounded
position — there isn't one to catch, by construction.

### 5.1 Protective Put

**Mechanics:** while holding (or alongside establishing) the underlying
position, buy a put option giving the right, not the obligation, to sell
the underlying at the strike price. If the underlying falls below the
strike, the put's gain offsets the underlying's loss below that point.

**Cost:** the option **premium**, paid upfront, known exactly at the time
the structure is proposed.

**What it caps:** downside loss below the strike is bounded. Maximum loss
= `(current price − strike) + premium paid` — a fixed, pre-computable
number, never dependent on how far the underlying subsequently falls.

**What it doesn't cap:** upside participation is fully preserved (minus
the premium's fixed drag on return in every scenario where the put isn't
exercised). This is a *cost* to be weighed, not a bound the structure
imposes.

### 5.2 Collar

**Mechanics:** while holding the underlying, simultaneously buy a
protective put (Section 5.1, the downside floor) and sell a **covered**
call against the same held position (an upside ceiling) — "covered"
specifically because the underlying already held is what would be
delivered if the call is exercised, not a naked short position. The call
premium received offsets some or all of the put premium paid.

**Why typically low-cost:** the two premiums roughly offset by
construction — a collar can often be structured near zero net cost
(a "zero-cost collar"), though this depends on strike selection and is
not guaranteed.

**What it bounds, both sides:** the position's value is bounded within
`[floor, ceiling]` regardless of how far the underlying moves in either
direction — the put's strike sets the floor, the call's strike sets the
ceiling, both known exactly when the structure is proposed.

### 5.3 Required Inputs for Pricing

Pricing either structure requires **implied volatility**, **strike
selection** (which available strikes are liquid/relevant for the
underlying), and **expiry** (available expiration dates). None of these
has a specified data source in this document — the same treatment already
established project-wide for every other real-market-data dependency
pending the Phase 3 vendor decision. The direct precedent: Cash
efficiency's `best_available_comparable_yield`
(`QUANT_ENGINE_SPEC.md`, Section 7) is likewise named as an assumed input
parameter with no data source specified. See Section 9, item 1 for what
remains open specifically about *this* data.

## 6. The Naked/Uncovered Options Prohibition — Structural, Not Advisory

**Any options position with unlimited or unbounded loss potential — a
naked (uncovered) call sale, a put sale without covering collateral —
must be structurally impossible for this system to generate. Not flagged
after the fact. Not rejected downstream. Impossible to produce in the
first place.**

The direct precedent is `OPTIMISATION_ENGINE_SPEC.md` Section 5.1a: the
loss cap there is enforced *inside the solver itself*, as a convex
constraint on the optimisation problem — "a candidate that would breach
the cap is infeasible to produce, not generated and then flagged." This
prohibition must follow the same principle, and be **at least as strict**,
given the more severe downside involved: a breached loss cap is a
(bounded, if too-large) number; an uncovered short option's loss is
unbounded in principle. If the loss-cap precedent justified enforcing
inside the solver rather than downstream, an unbounded-loss position
justifies it more, not less.

Concretely, for the two structures this version supports:

- Both the protective put and the collar are bounded-loss **by
  construction** (Section 5.1/5.2) — correctly identifying a candidate
  *as* one of these two structures is sufficient to guarantee its maximum
  loss is finite and known. No separate enforcement step is needed for
  these two specifically, because the structures themselves cannot
  represent an uncovered position — a protective put requires holding (or
  concurrently establishing) the underlying; a collar's call leg is
  covered by the same held underlying, by definition.
- **This section is not scoped to only what this v1 document happens to
  include.** It is a standing, project-wide structural principle for
  *any* options capability this system ever builds, present or future
  (Section 1's excluded future scope included): whatever engine
  eventually owns options-structure generation (Section 7) must make an
  uncovered position mathematically infeasible to emit from its
  generation logic itself — the same way `minimize_variance_with_loss_cap`
  makes a cap-violating candidate infeasible to solve for, not merely
  something checked after the fact.
- `verification-engine`'s independent re-check (Section 7 below) is
  **defense-in-depth**, not the primary enforcement mechanism — the same
  distinction `OPTIMISATION_ENGINE_SPEC.md` Section 8, item 2 already
  draws for gate-checking: "it means a gated action can't even exist as a
  candidate, rather than relying solely on `ai-engine` to refrain from
  framing it or `verification-engine` to catch it downstream." The same
  reasoning applies here, for the same reason, with a more severe failure
  mode if it's ever relied on as the *only* layer.

## 7. Relationship to Existing Engines — Proposed, Not Yet Confirmed

**Hedge ratio and Greeks calculation: proposed `quant-engine`.** For
consistency with where every other risk metric already lives
(`QUANT_ENGINE_SPEC.md` Sections 5.2/5.3), and because hedge ratio
calculation reuses that package's existing covariance/variance machinery
directly (Section 4.1 above). This is a **proposal**, not a foregone
conclusion — unlike Capital Efficiency Score's ownership
(`QUANT_ENGINE_SPEC.md` Section 4, a dedicated formal-resolution section),
no equivalent resolution exists for this document. A follow-up patch to
`QUANT_ENGINE_SPEC.md` would be needed to make this a decision rather than
a proposal.

**Constructing an actual hedged position or options structure candidate:
proposed `optimisation-engine`.** Extending its existing constraint-
taxonomy pattern (`OPTIMISATION_ENGINE_SPEC.md` Section 6, and Section 8
below) the same way `minimize_variance_with_loss_cap` extended
`minimize_variance`. Also a proposal, also needing its own formal-
resolution patch to `OPTIMISATION_ENGINE_SPEC.md` before it is a decision.

**`verification-engine`'s independent re-check:** mirroring
`verify_loss_cap_candidate`'s existing pattern exactly —
`VERIFICATION_FRAMEWORK.md` Section 5.5's principle applied to this new
domain. Concretely, this means: re-derive the proposed structure's
hedge ratio and maximum-loss bound independently, directly from
`quant-engine`'s own already-tested formulas (Section 4.1), **never**
calling `optimisation-engine`'s own generation logic — the same
independence `verify_loss_cap_candidate` already achieves by recomputing
VaR via `quant-engine`'s `parametric_var` rather than trusting
`optimisation-engine`'s self-report. This independent recomputation is
what confirms, a second time and from a different code path, that a
structure genuinely satisfies Section 6's prohibition and the Mandate's
own stated loss tolerance — not a rubber stamp on `optimisation-engine`'s
own claim.

## 8. Constraint Taxonomy

Extends `OPTIMISATION_ENGINE_SPEC.md` Section 6's existing taxonomy:

- **Hard constraints** — must never be violated:
  - The naked/uncovered options prohibition (Section 6) — stricter than
    the existing hard-constraint pattern's "Violation → automatic
    `REJECT` in Stage 9b" (`OPTIMISATION_ENGINE_SPEC.md` Section 6): an
    uncovered position must never be *generated*, not generated and then
    rejected.
  - The Mandate's existing `max_single_period_loss` and maximum
    acceptable drawdown (`DATA_ARCHITECTURE.md` Section 4.1) apply
    identically to hedged positions and options structures. "Bounded"
    (Section 6) is necessary but not sufficient — a protective put or
    collar with a computable, finite max loss that still *exceeds* the
    Mandate's stated tolerance must be rejected the same way an
    unconstrained-but-too-large candidate already is
    (`OPTIMISATION_ENGINE_SPEC.md` Section 5.1a).
  - Regulatory/gate constraints, same as every other engine
    (`MVP_ROADMAP.md` Gate C) — see Section 3.
- **Soft constraints / preferences** — deprioritise or `FLAG`, not
  automatic rejection (exact treatment inherited as open from
  `OPTIMISATION_ENGINE_SPEC.md` Section 10, item 2, not re-litigated
  here): premium/cost budget preference, preferred expiry range, and —
  specific to the collar — willingness to cap upside, since giving up
  upside via the covered-call leg is a real tradeoff a user might weight
  differently.

## 9. Known Gaps / Open Questions

1. **Options pricing data source.** No vendor is chosen, consistent with
   the project-wide Phase 3 deferral. Beyond that: `DATA_SOURCE_REGISTRY.md`'s
   existing category taxonomy (Category A, "Market & Pricing Data") does
   not explicitly name options chains or implied-volatility surfaces as a
   sub-category — whether Category A already covers this or needs an
   explicit extension is itself unresolved, not decided here.
2. **Rebalancing cadence for dynamic hedging** (Section 4.3) — cadence and
   trigger are both genuinely open, not resolved by an invented default.
3. **Engine ownership** (Section 7) — `quant-engine` for hedge
   ratio/Greeks and `optimisation-engine` for structure construction are
   both proposals. Neither has the formal-resolution treatment
   `QUANT_ENGINE_SPEC.md` Section 4 gave Capital Efficiency Score
   ownership. Follow-up patches to both documents would be needed.
4. **Regulatory treatment of options-based structures.**
   `REGULATORY_BOUNDARIES.md` does not address options or derivatives
   anywhere in its current text. Whether these structures require
   different FCA treatment (e.g. complex-instrument appropriateness
   assessment) beyond the existing advice-vs-guidance question (Section
   3.1 of that document) has not been analysed and is not assumed here.
5. **Whether Gate C's execution boundary needs its own confirmation for
   options specifically.** This document assumes options-based hedge
   recommendations follow the same non-execution boundary as every other
   engine's candidates (Section 3) — but options carry different
   settlement/execution mechanics than simple equity trades, and that
   assumption has not been explicitly confirmed by anyone with authority
   over Gate C; it is carried over by analogy, not verified.
6. **Options pricing model.** Whether Greeks/implied-volatility-derived
   values are computed via Black-Scholes, a binomial model, or something
   else is not chosen here — mirroring `QUANT_ENGINE_SPEC.md` Section 11,
   item 5's treatment of the (also still-open) VaR methodology choice:
   named, not resolved.
7. **Minimum hedge effectiveness.** Whether any minimum `R²` (Section 4.1)
   is required before a hedge is recommendable at all, or whether any
   positive improvement is presented with its own effectiveness disclosed
   and left to the user/CIO to judge, is not decided.
8. **Basis-risk disclosure.** Whether the residual `(1 − R²) × Var(ΔS)`
   (Section 4.2) should be a required, explicit field on a hedge
   recommendation's `UAP` output is a reasonable expectation but is not
   specified precisely enough here to be considered decided.
