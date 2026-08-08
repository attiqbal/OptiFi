# PRODUCT_VISION

**Status:** DRAFT (v1.5 — Phase 2A, patch: Section 1 stale reference corrected)

## 1. Purpose & Scope

This document defines what OptiFi is, who it is for, and the principles that
govern the product experience. It does not define screens, navigation, or
visual design — see Phase 2B (`APP_UX_BLUEPRINT.md`). It does not define
frontend technology — see Phase 2C (`FRONTEND_SPEC.md`, not yet written).

## 2. Relationship to Prior Documents

This document sits downstream of, and must remain consistent with,
`ENGINE_PIPELINE_SPECIFICATION.md` (Phase 1A) and `ANALYTICAL_CONTRACT_SPEC.md`
(Phase 1B). Where this document illustrates the intelligence engine with a
simplified diagram (Section 12), that illustration is descriptive and
product-facing only — `ENGINE_PIPELINE_SPECIFICATION.md` remains the
authoritative technical definition, and if the two ever diverge, that
document governs.

## 3. Product Definition

**OptiFi is a Personal Financial Intelligence and Capital Optimisation
Platform.** Its fundamental question:

> Given everything happening in markets, the economy, and the user's own
> financial position, what is the smartest thing for their capital to do
> now?

OptiFi is explicitly **not**:

* a budgeting app
* a stock screener
* a trading bot
* a news aggregator
* a robo-adviser
* an accounting system
* an LLM wrapper around financial data

It combines relevant financial intelligence into a personalised AI CIO. The
long-term experience should feel like giving an individual or business owner
access to a private investment research department.

## 4. Two-Layer Architecture (Conceptual)

**Layer A — OptiFi Intelligence Engine.** The infrastructure defined in the
Phase 1 documents. It continuously: observes → validates → understands →
models → forecasts → simulates → evaluates → optimises → verifies. Every
stage transforms its inputs into a more structured, validated form and never
silently invents missing information (Phase 1A, Section 4).

**Layer B — OptiFi App.** What the user sees. It translates the analytical
infrastructure into four questions: What changed? Why does it matter to me?
What should I consider doing? What happens if I'm wrong? That simplicity is
a core product principle — the concrete screens that deliver it belong to
Phase 2B, not this document.

## 5. Core User Promise

OptiFi should eventually be able to say, in substance:

> Your capital is currently 84% efficient. I identified three developments
> affecting your portfolio today. One requires attention; two require no
> action. I found approximately £3,420/year of potential capital-efficiency
> improvements. Your current risk remains within your selected range. Here
> is what I would consider doing, and why.

The user should not have to analyse the underlying data themselves — the
system does the analytical work.

## 6. Target Users & Scope

The architecture supports both individual and business capital under the
same objective.

**Individual** — in scope: cash, savings, stocks, ETFs, funds, bonds,
pension, ISA, property, crypto where permitted, mortgages, loans.

**Business** — in scope: cash, deposits, money-market holdings,
investments, borrowing, FX, working liquidity, excess capital, short-term
investment requirements. **Explicitly out of scope:** HR, employee
scheduling, CRM, payroll administration, or any other business
administration function. OptiFi concentrates on capital and treasury only —
this boundary is intentional and should not expand without a deliberate
decision.

**Tax & Estate Intelligence** — in scope, across three tiers of increasing
regulatory sensitivity. **Tier 1 — tax-aware optimisation**: full use of
tax-advantaged wrappers, CGT/dividend threshold awareness, and tax-loss
harvesting flags; this is computational and sits inside the existing
optimisation-engine constraint set. **Tier 2 — general tax/estate
education**: explains how IHT, CGT, and trust taxation work in the
abstract, with no structuring recommendation tailored to the user. **Tier
3 — personalised trust/charity structuring, flag-only**: OptiFi may flag,
from the Financial Twin, that a user's circumstances suggest professional
estate/tax planning could be valuable. **OptiFi does not originate a
specific trust or charitable structure.** The product's role stops at
facilitating a handoff to a qualified solicitor/STEP practitioner (for the
legal structure) and a registered tax adviser (for tax treatment).
Representing a trust or charitable vehicle the user already has as part of
the Financial Twin is unaffected by this restriction — the boundary is on
originating new structures, not describing existing ones.

## 7. The Financial Twin (Conceptual)

Every user has a continuously updated, machine-readable representation of
their financial life: assets, liabilities, portfolio characteristics
(sector/country/currency/factor exposure, concentration), objectives, risk
tolerance, liquidity requirements, investment horizon, and constraints. This
becomes the context against which every piece of financial information is
evaluated. Its precise data model belongs to `DATA_ARCHITECTURE.md` and
`ECONOMIC_ONTOLOGY.md`, not this document — this section states the concept
and its role, not its schema. The twin's asset model includes existing
trust holdings and charitable-giving vehicles where the user already has
them — these are represented as `FACT`, consistent with any other holding,
and are distinct from the Tier 3 restriction (Section 6) on originating new
structures.

## 8. The User Mandate (Conceptual)

Before OptiFi gives meaningful personalised analysis, the user defines a
Financial Mandate — for example: a risk-tolerance rating, a maximum
acceptable drawdown, an investment horizon, a minimum cash reserve, maximum
individual-position and sector-allocation limits, a crypto ceiling, a
leverage policy, and a stated objective. For now, the mandate defines the
boundaries within which analysis operates. It later becomes the boundary
within which any agentic execution (Section 13) is permitted to act.

## 9. The CIO Philosophy

The Manager/CIO layer (Phase 1A, Stage 12; `ai-engine`) reasons in sequence:
what does the user want to know → which specialists are needed → is their
information current → do their conclusions agree → are we missing something
→ does verification pass → only then, what to tell the user. This is
**analytical orchestration**, distinct from the backend's **technical
orchestration** (Phase 1A, Section 11) — the CIO reasons across specialist
outputs; the backend routes requests and data between services. That
separation must hold as the product evolves.

## 10. Information Trust Philosophy

Every conclusion OptiFi presents is one of `FACT`, `ESTIMATE`, or
`JUDGEMENT`, each carrying a `validation_status`, per the definitions in
`ANALYTICAL_CONTRACT_SPEC.md` (Phase 1B) — this document does not redefine
them. As a product principle: these distinctions must remain visible to the
user in some form, and confidence in a conclusion must be inspectable, not
just asserted. Exactly how that is surfaced visually is a Phase 2B decision;
the principle that it must be surfaced at all is a Phase 2A (product-level)
commitment.

## 11. Forecasting Philosophy

OptiFi never states "this will happen." It states "these futures appear
plausible," expressed as a distribution across scenarios, consistent with
Phase 1A's treatment of forecasts and simulations as `ESTIMATE`-class
output. The value of the system is not predicting the single winning
scenario — it is finding strategies that remain sensible across plausible
futures. This principle should inform every user-facing forecast or
scenario output the product ever produces.

## 11a. Capital Efficiency Score Principle

The Capital Efficiency Score is a headline product metric (see
`APP_UX_BLUEPRINT.md`, Section 14 for its display) and must be computed
from transparent, deterministic quantitative rules — never invented,
estimated, or asserted by the LLM. It is `FACT`/`ESTIMATE`-class output,
never `JUDGEMENT`. The CIO may explain the score; it does not decide it.
Which engine owns the computation is not finalised — see Section 18.

## 12. Illustrative Engine Mapping (Non-Authoritative)

The following is a simplified, product-facing illustration of how the
intelligence engine supports the product experience. **It is descriptive
only.** The authoritative stage definitions and engine ownership are in
`ENGINE_PIPELINE_SPECIFICATION.md`, Sections 9–10.

```text
EXTERNAL / INTERNAL DATA
          ↓
DATA ENGINE → VALIDATION → STRUCTURED EVENTS → KNOWLEDGE LAYER
          ↓
CAUSAL ENGINE → FORECAST ENGINE → SIMULATION ENGINE
          ↓
QUANT / PORTFOLIO ENGINE → OPTIMISATION ENGINE
          ↓
CANDIDATE FRAMING (ai-engine) → VERIFICATION ENGINE
          ↓
CIO / MANAGER (ai-engine)
          ↓
OPTIFI APP
```

Users should feel, informally, as though they have an analyst team behind
the product — some "analysts" are LLMs, some are mathematical models, some
are statistical engines, some are databases. The user does not need to know
which is which; OptiFi selects the right tool for each task (Phase 1A,
Section 3). A literal org-chart illustration of this idea belongs to Phase
2B, not this document.

## 13. Execution Roadmap

The product's relationship to actually moving money deepens in stages:

1. **Analyse** — describe the user's position and what changed.
2. **Recommend** — propose specific candidate actions (Phase 1A, Stages 9–10).
3. **Prepare** — stage a transaction for review, not yet executed.
4. **User approves** — explicit human authorisation.
5. **Agent executes within mandate** — bounded, permissioned execution.

**This roadmap is gated by regulation, not just engineering.** Stages 2
onward — and especially 4–5 — depend directly on how OptiFi is classified
under `REGULATORY_BOUNDARIES.md` (advice vs. guidance), which remains an
open, unresolved question. No stage beyond 1 should be treated as a target
date without that resolution. A "KYA framework" is referenced informally as
relevant to bounded agent execution — **this framework is not yet defined in
any OptiFi document** and must be specified before Stage 5 is designed in
any further detail.

## 14. MVP Definition (V0.1)

Discipline matters here — V0.1 does not need every capability described in
this document. V0.1 scope: one user; one manually entered portfolio; 20–30
equities/ETFs; a basic risk profile; live or near-live prices; a small set
of macro indicators; a small set of financial news sources; portfolio
analytics; basic causal intelligence; a small number of forecasts; scenario
simulation; CIO synthesis. Success criterion: OptiFi can reliably,
transparently, and personally answer "what are the three most important
developments affecting my portfolio today?" This section is the seed for
`MVP_ROADMAP.md`, which remains a placeholder and should eventually be
populated from this section — not performed in this task.

## 15. The Moat

If OptiFi succeeds as a company, the durable advantage is unlikely to be the
app itself. It is the combination of: the financial ontology, historical
validated data, causal relationships, forecasting models, model-performance
history, portfolio optimisation, the personalised financial twin, and
recommendation-outcome history. The LLM interface layer could change over
time; the underlying intelligence infrastructure is the asset that persists.

## 16. North Star Statement

> OptiFi turns global financial information into personalised, verifiable
> decision intelligence by combining specialised quantitative models,
> causal analysis, forecasting, simulation, and AI orchestration around a
> continuously updated model of the user's capital.

> The objective is not to predict the future perfectly. It is to help the
> user make better financial decisions across plausible futures.

## 17. Deferred to Future Documents

The following are deliberately excluded from this document and belong to
later phases:

* App navigation structure, screen-by-screen design, and mockups → Phase 2B
  (`APP_UX_BLUEPRINT.md`)
* The "Today" home screen, Opportunity Feed, Portfolio screen, asset/company
  research screen, Scenario Lab UI, "Why?" drill-down interaction, and
  business-mode screen → Phase 2B
* A literal analyst-team org-chart illustration → Phase 2B
* Frontend technology, component architecture, state management → Phase 2C
  (`FRONTEND_SPEC.md`)
* Behavioural risk profiling (stated vs. revealed risk tolerance) — noted as
  a future direction, not MVP; the architecture should not preclude it later,
  but it is not designed here and raises its own consent/regulatory
  questions.

## 18. Known Gaps / Open Questions Carried Forward

1. The "KYA framework" referenced in Section 13 is undefined anywhere in
   OptiFi's documentation and needs a formal specification before any
   further design of Stage 5 (agent execution).
2. Execution Stages 2–5 (Section 13) depend on the unresolved advice-vs-
   guidance classification in `REGULATORY_BOUNDARIES.md`.
3. ~~The Financial Twin's actual schema (Section 7) still needs to be
   defined in `DATA_ARCHITECTURE.md` / `ECONOMIC_ONTOLOGY.md`...~~
   **RESOLVED:** `DATA_ARCHITECTURE.md` and `ECONOMIC_ONTOLOGY.md` now
   deliver this schema (Phase 5-1/5-2). Storage technology, ontology
   governance, and mandate-freshness cadence remain open — see those
   documents' own Section 8 and Section 7 respectively.
4. ~~The Capital Efficiency Score is asserted as a product-level
   metric... but which engine owns computing it is not decided here.~~
   **RESOLVED — duplicate of item 8:** this item and item 8 asked the
   same question under different drafts of this section. See item 8:
   `QUANT_ENGINE_SPEC.md` Section 4 formally assigns this to
   `quant-engine`. Retained here, marked resolved, to preserve the audit
   trail rather than silently deleted.
5. Business mode's boundary ("capital and treasury, not administration") may
   need a formal, explicit exclusion list once business features are
   designed in Phase 2B, similar in spirit to the non-goals lists used in
   Phase 0/1.
6. ~~Whether Phase 2B and 2C should also produce their own...~~
   **RESOLVED:** `APP_UX_BLUEPRINT.md` (Phase 2B) does both, in its
   Sections 2 and 17 — that is now the confirmed convention.
7. Tax & Estate Intelligence's regulatory treatment (Section 6) was
   deferred to Phase 3 and is now addressed in
   `REGULATORY_BOUNDARIES.md`, Sections 3.2–4.3. **The underlying legal
   question is still open** — see `REGULATORY_BOUNDARIES.md` Section 6,
   items 1 and 6, which this document defers to rather than restating.
8. ~~Which engine (or dedicated component) computes the Capital
   Efficiency Score (Section 11a) is not finalised.~~ **RESOLVED:**
   `QUANT_ENGINE_SPEC.md` Section 4 formally assigns this to
   `quant-engine`. (Item 4 asked the same question under an earlier draft
   of this section and is now cross-referenced to this resolution.)
