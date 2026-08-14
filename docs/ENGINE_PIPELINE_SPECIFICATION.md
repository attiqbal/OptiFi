# ENGINE_PIPELINE_SPECIFICATION

**Status:** DRAFT (v2.8 — Phase E5, patch: Section 12 item 6 added — replay-engine ownership)

## 1. Revision Notes (v1 → v2)

- Removed `PROVISIONAL_FACT` as a fourth information class. There are exactly
  three information classes: `FACT`, `ESTIMATE`, `JUDGEMENT`.
- Added `validation_status` as an independent second axis, applied to every
  output regardless of information class — answers "how much do we trust
  this right now," separately from "what kind of information is this."
- Formally approved `information_class` and `validation_status` into the
  Universal Analytical Packet (Section 6).
- Split Stage 9 into 9a (candidate generation) and 9b (policy/constraint
  validation), and renamed/constrained Stage 10 so `ai-engine` frames and
  explains candidates but cannot invent or alter the underlying financial
  action.
- Added a Multi-Model Disagreement Preservation principle (Section 7):
  specialist engines must preserve competing model outputs as a plural set
  rather than collapsing them before the CIO layer sees them.
- Engine ownership (Section 10), the analytical/technical orchestration
  distinction (Section 11), independent verification (Stage 11), and Stage
  14's unresolved ownership are unchanged from v1.

## 2. Purpose & Scope

This document defines how information moves through OptiFi's analytical
systems, the classifications that information carries, and which engine
folder (from Phase 0) owns each stage. It does not select technologies,
algorithms, providers, or libraries — those remain out of scope until a later
phase.

## 3. Core Vision

OptiFi is not a single LLM that reads financial information and generates
opinions. It is a modular **Financial Intelligence Engine** composed of
specialised analytical systems. Each analytical task is assigned to the type
of system best suited to perform it reliably:

- deterministic calculations for arithmetic and portfolio metrics
- statistical methods for risk analysis
- econometric/time-series/ML models for numerical forecasting
- optimisation methods for constrained capital allocation
- knowledge graphs for persistent entity relationships
- causal models for economic transmission mechanisms
- simulation models for scenario propagation
- LLMs for unstructured-text interpretation, qualitative reasoning,
  orchestration, synthesis, contradiction handling, and explanation

The LLM behaves like a **CIO / analytical manager**, coordinating specialist
systems rather than replacing them.

## 4. Non-Negotiable Principle

OptiFi must be:

> **Grounded at every analytical stage.**

Each stage transforms its inputs into a more useful, structured, validated
form before passing information onward. No stage may silently invent missing
information. No downstream stage should consume raw information when an
upstream specialist exists whose job is to validate, structure, calculate, or
interpret it first.

The analytical chain must be: traceable, reproducible, inspectable,
falsifiable, uncertainty-aware, modular, and independently verifiable.

## 5. Information Classification

Every piece of information in OptiFi is classified along **two independent
axes**. Conflating them was the main error corrected in this revision.

### 5.1 Information Class — "what kind of information is this?"

**FACT**
Information directly supported by validated external or internal data (an
official CPI release, a security price, reported company revenue, a verified
portfolio holding). Facts carry provenance and time information. Facts are
not forecasts.

**ESTIMATE**
Outputs produced by analytical, statistical, econometric, ML, quantitative,
causal, or simulation systems (expected volatility, forecast GDP growth,
simulated drawdown). Estimates expose uncertainty, methodology identity,
relevant assumptions, and model limitations. Estimates are not facts.

**JUDGEMENT**
Interpretations, conclusions, comparisons, or decision-oriented reasoning
derived from facts and estimates ("the portfolio appears unusually exposed to
duration risk"). Judgements must be traceable to the facts and estimates
supporting them and must never be presented as observed facts.

### 5.2 Validation Status — "how much do we trust it right now?"

Applies to `FACT`, `ESTIMATE`, and `JUDGEMENT` alike. **This document
defers to `ANALYTICAL_CONTRACT_SPEC.md` Section 4 as authoritative for the
full definition and current value list** (as of this patch: `VERIFIED`,
`PROVISIONAL`, `CONFLICTED`, `STALE`, `INCOMPLETE`, `REJECTED`,
`SUPERSEDED`) — see that document rather than duplicating the list here
going forward.

Example: an LLM-extracted claim from a news article is
`information_class: FACT`, `validation_status: PROVISIONAL` — not a
separate "provisional fact" class.

### 5.3 Fundamental Rule

Every important user-facing statement must be attributable to an
`information_class` (`FACT` / `ESTIMATE` / `JUDGEMENT`) and carry a
`validation_status`. OptiFi must never blur these categories, and must never
present a non-`VERIFIED` item to a user without surfacing its status.

## 6. Universal Analytical Packet

**This document defers to `ANALYTICAL_CONTRACT_SPEC.md` Section 5 as
authoritative** for the full Universal Analytical Packet field list — see
that document rather than duplicating it here going forward. As of this
patch, the authoritative field set adds `id`, `subject`, `producer`,
`evidence_as_of`, `generated_at`, `provenance_chain`, and
`disagreement_set_ref` to the original `result`, `information_class`,
`validation_status`, `evidence`, `source`, `confidence`, `assumptions`,
`limitations`, and `dependencies`.

This is a schema *shape*, not an implementation. Field types, storage, and
validation logic are out of scope for this document.

## 7. Multi-Model Disagreement Preservation

When more than one model produces a result for the same target (e.g. an
econometric forecast, an ML forecast, and a market-implied forecast for
recession probability; or a valuation model, a momentum model, and a quality
model disagreeing on direction), the specialist engine that produced them
must preserve all of them as a **plural set of `ESTIMATE` entries**, each
with its own methodology identity, confidence, and `validation_status` — it
must not silently collapse them into a single number before passing them
downstream.

If the set contains genuine disagreement, the engine marks it as such rather
than resolving it. Any future aggregation/ensemble mechanism must be an
explicit, separately specified process owned by the relevant specialist
engine (most likely `forecast-engine` for forecasts) — **not** a judgement
call made implicitly by the CIO/manager LLM. Designing that mechanism is
deferred; this document only establishes that disagreement must survive
intact until Stage 12, where it is explained to the user rather than
mathematically resolved.

## 8. The Intelligence Pipeline

```text
EXTERNAL / INTERNAL SOURCES
          ↓
1.  DATA ACQUISITION                              → data-engine
          ↓
2.  VALIDATION & NORMALISATION                     → data-engine
          ↓
3.  STRUCTURED FACT / EVENT EXTRACTION             → data-engine (+ ai-engine for unstructured text)
          ↓
4.  FINANCIAL & ECONOMIC KNOWLEDGE LAYER           → data-engine + causal-engine (joint)
          ↓
5.  CAUSAL ANALYSIS                                → causal-engine
          ↓
6.  FORECASTING                                    → forecast-engine
          ↓
7.  SCENARIO GENERATION & SIMULATION                → simulation-engine
          ↓
8.  PORTFOLIO / USER IMPACT ANALYSIS               → quant-engine
          ↓
9a. OPTIMISATION — CANDIDATE GENERATION            → optimisation-engine
          ↓
9b. POLICY / CONSTRAINT VALIDATION                 → optimisation-engine
          ↓
10. CANDIDATE FRAMING & EXPLANATION                → ai-engine (frames only, does not alter candidates)
          ↓
11. INDEPENDENT VERIFICATION                       → verification-engine
          ↓
12. CIO / MANAGER SYNTHESIS                        → ai-engine
          ↓
13. USER-FACING EXPLANATION                        → ai-engine (content) + backend/frontend (delivery)
          ↓
14. OUTCOME TRACKING & MODEL EVALUATION            → UNRESOLVED (see Section 12)
```

## 9. Stage-by-Stage Specification

**Stage 1 — Data Acquisition** (`data-engine`)
Purpose: retrieve raw data from external and internal sources without
transformation. Produces: raw, unclassified payloads with source and
retrieval-timestamp metadata. Failed retrievals must be reported, never
silently dropped.

**Stage 2 — Validation & Normalisation** (`data-engine`)
Purpose: check raw data for structural validity, staleness, duplication, and
schema conformance; normalise units and formats. Data failing checks is
quarantined and flagged — never silently corrected or discarded without a
record.

**Stage 3 — Structured Fact / Event Extraction** (`data-engine`, with
`ai-engine` support for unstructured text)
Purpose: convert validated data into structured facts/events. Always
produces `information_class: FACT`. For structured numeric/tabular sources
(prices, official releases), this is deterministic parsing and typically
carries `validation_status: VERIFIED`. For unstructured sources (news,
filings prose), this requires LLM-assisted interpretation and must carry
`validation_status: PROVISIONAL` until corroborated by a second source or a
structured record. This is the one point in the pipeline where an LLM
contributes to fact-like output, and its trust level must be explicit, never
silently upgraded to `VERIFIED`.

**Stage 4 — Financial & Economic Knowledge Layer** (`data-engine` +
`causal-engine`, joint)
Purpose: maintain the persistent structured knowledge base of entities,
relationships, and classifications that later stages query. Directly-observed
relationships (e.g. corporate ownership structure) are `FACT`;
inferred/statistical relationships are `ESTIMATE`. Both carry an appropriate
`validation_status`.

**Stage 5 — Causal Analysis** (`causal-engine`)
Purpose: model economic/financial transmission mechanisms between entities
and events. Produces `ESTIMATE` with confidence, methodology identity, and
assumptions. Where multiple causal models disagree, apply Section 7
(preserve as a plural set).

**Stage 6 — Forecasting** (`forecast-engine`)
Purpose: produce numerical forecasts for relevant financial/economic
variables. Produces `ESTIMATE` with explicit uncertainty bounds. Where
multiple models (econometric, ML, market-implied) disagree, apply Section 7
— all are preserved, none is silently chosen.

**Stage 7 — Scenario Generation & Simulation** (`simulation-engine`)
Purpose: construct and propagate scenarios using Stage 5 and Stage 6 outputs
to estimate downstream effects. Produces `ESTIMATE`, scenario-conditional.

**Stage 8 — Portfolio / User Impact Analysis** (`quant-engine`)
Purpose: translate facts, estimates, and simulated scenarios into
quantitative portfolio- and user-level metrics (exposure, risk, performance
impact). Directly-computed arithmetic from verified holdings (e.g. current
portfolio value) is `FACT`; anything derived from a risk or exposure model is
`ESTIMATE`. These must not be blended into one undifferentiated number.

**Stage 9a — Optimisation: Candidate Generation** (`optimisation-engine`)
Purpose: given user constraints (risk tolerance, liquidity, tax, ESG,
exclusions) and Stage 8's impact analysis, compute candidate actions with
their expected quantitative impact (e.g. expected risk reduction, expected
return impact). Produces `ESTIMATE`. Output must expose the constraint set
and objective assumptions used, not the optimisation method itself.

**Stage 9b — Policy / Constraint Validation** (`optimisation-engine`)
Purpose: check each candidate from 9a against the full constraint set
(regulatory, user-defined exclusions, business policy rules) and attach a
pass/fail/partial verdict — conceptually similar to Stage 11 but scoped
specifically to policy compliance. A candidate that fails a hard constraint
must be marked `REJECTED` and excluded from what reaches Stage 10.

**Stage 10 — Candidate Framing & Explanation** (`ai-engine`)
Purpose: explain and contextualise the candidates that survived Stage 9b,
using upstream causal/forecast/scenario context (Stages 5–7) to say why a
candidate matters. **Hard constraint: `ai-engine` must not invent, alter, or
substitute a different financial action than what Stage 9a/9b produced and
validated.** It may rank, compare, and narrate; it may not create new
candidate actions or change their quantitative parameters. Produces
`JUDGEMENT` — the framing is interpretive, but the embedded financial figures
remain traceable, unmodified, to Stage 9a's `ESTIMATE` output.

**Stage 11 — Independent Verification** (`verification-engine`)
Purpose: independently check candidates and their supporting facts/estimates/
judgements for consistency, contradiction, staleness, and plausibility.
Produces a verdict reflected via `validation_status` on the existing outputs
— not a new information class.

**Stage 12 — CIO / Manager Synthesis** (`ai-engine`)
Purpose: the *analytical* orchestration layer — weighs verified candidates,
resolves conflicts between specialist outputs, forms the final judgement.
Produces `JUDGEMENT`, referencing all supporting outputs and verification
verdicts. **The CIO must not mathematically resolve disagreement between
multiple `ESTIMATE` entries from the same specialist engine** (e.g.
competing forecasts) by silently picking or averaging one — it may explain
the disagreement per Section 7. This is distinct from *technical*
orchestration — see Section 11.

**Stage 13 — User-Facing Explanation** (`ai-engine` for content generation;
`backend`/`frontend` for delivery)
Purpose: translate the CIO synthesis into human-readable explanation while
preserving `information_class` and `validation_status` distinctions — never
flattened into undifferentiated prose. A non-`VERIFIED` item reaching the
user must say so.

**Stage 14 — Outcome Tracking & Model Evaluation** (`evaluation-engine`)
Purpose: track realised outcomes against forecasts/recommendations over time
and feed evaluation results back into model confidence calibration.
**RESOLVED in Phase E3** — see Section 12, item 1, and
`FORECAST_ENGINE_SPEC.md` Section 7 for the forecast-evaluation methodology
this stage implements first.

## 10. Engine Ownership Summary

| Engine folder | Pipeline stage(s) | Phase 0 capability # |
|---|---|---|
| `data-engine` | 1, 2, 3 (structured), 4 (joint) | 1–5 |
| `causal-engine` | 4 (joint), 5 | 6 |
| `quant-engine` | 8 (incl. Capital Efficiency Score — see `QUANT_ENGINE_SPEC.md`) | 7–8 |
| `forecast-engine` | 6 | 9 |
| `simulation-engine` | 7 | 10 |
| `optimisation-engine` | 9a, 9b | 11 |
| `ai-engine` | 3 (unstructured support), 10, 12, 13 | 12, 14 |
| `verification-engine` | 11 | 13 |
| `evaluation-engine` | 14 | — |

## 11. Analytical vs. Technical Orchestration

Two different things are both loosely called "orchestration" in OptiFi and
must not be conflated:

- **Analytical orchestration** — Stage 12's CIO/manager reasoning across
  specialist outputs. Owned by `ai-engine`. This document's concern.
- **Technical orchestration** — routing requests and data between engine
  services at runtime. Owned by `backend`. Out of scope for this document;
  belongs in `SYSTEM_ARCHITECTURE.md`.

## 12. Known Gaps / Open Questions Carried to Phase 1B

1. ~~Which engine owns **Stage 14 (Outcome Tracking & Model Evaluation)**...~~
   **RESOLVED (Phase E3):** a new top-level engine folder, `evaluation-engine`,
   was created — the smallest coherent change consistent with this
   document's own "one engine folder per stage (or documented joint
   ownership)" convention (Section 10). Two alternatives were considered
   and rejected, documented here rather than decided silently:
   - **Extending `verification-engine`** — rejected. Stage 11
     (`verification-engine`) independently checks candidates and their
     supporting facts/estimates/judgements *at decision time*
     (consistency, contradiction, staleness, plausibility); Stage 14
     tracks realised outcomes *after the fact*, over time, against
     forecasts specifically. Conflating "is this candidate internally
     sound right now" with "did this forecast turn out to be right" would
     blur two genuinely different concerns this document has otherwise
     kept cleanly separated stage by stage.
   - **Extending `forecast-engine` itself** — rejected.
     `FORECAST_ENGINE_SPEC.md` Section 7 already anticipated this and
     deliberately framed evaluation as belonging to "whoever eventually
     owns" Stage 14, distinct from Stage 6's forecast-*production*
     concern. Folding evaluation into `forecast-engine` would also wrongly
     scope Stage 14 to forecasts only — Stage 14's own purpose (tracking
     realised outcomes against forecasts *and recommendations*) already
     names a second consumer (Stage 9a/10 candidates) that has nothing to
     do with `forecast-engine`.
   - **An `infrastructure`/observability concern** — rejected. Stage 14's
     work (target-appropriate metrics, calibration, model scorecards,
     ensemble-weighting inputs) is analytical logic requiring UAP-level
     domain knowledge (`information_class`, `validation_status`,
     `disagreement_set_ref`, `supersede()`), not a generic
     logging/metrics-pipeline concern `infrastructure` otherwise owns.

   This is an architectural decision, not a product/regulatory one — made
   here because `FORECAST_ENGINE_SPEC.md` Section 7 and this document's own
   Part E-equivalent brief explicitly delegated "inspect the architecture
   and propose the smallest coherent change" to whoever implemented Stage
   6's evaluation counterpart. See `evaluation-engine/README.md` for the
   package itself.
2. ~~Does Stage 9b belong inside `optimisation-engine`...~~ **RESOLVED:**
   `OPTIMISATION_ENGINE_SPEC.md` Section 4 formally confirms
   `optimisation-engine` owns both Stage 9a and Stage 9b.
3. ~~What mechanism corroborates a `PROVISIONAL` fact into `VERIFIED`...~~
   **RESOLVED:** see `ANALYTICAL_CONTRACT_SPEC.md` Section 4a
   (independent corroboration or structured cross-check; shared-origin
   republication does not count).
4. Does `REGULATORY_BOUNDARIES.md` need to say anything about non-`VERIFIED`
   output (`PROVISIONAL`, `CONFLICTED`) reaching a user before resolution?
   Flagged, not answered.
5. ~~What is the actual ensemble/aggregation mechanism...~~
   **RESOLVED:** `FORECAST_ENGINE_SPEC.md` Section 6 designs the
   mechanism for forecast disagreement (simple-average and
   inverse-error-weighting formulas). `QUANT_ENGINE_SPEC.md` Section 10
   separately decided factor/signal disagreement is NOT aggregated — it
   is preserved as a plural set only, with no ensemble computed. Both
   branches of this question are now answered, asymmetrically by design.
6. Should this document's `Status` field move from `DRAFT (v2)` to a
   versioned approval state once reviewed, and what is that process?
7. **Added and resolved (Phase E5):** historical replay/backtesting —
   reconstructing exactly what OptiFi could have known and concluded at
   a historical point in time, then evaluating the resulting decision
   against what later occurred — had no owner anywhere in this
   document. It is not one of the 14 stages; it is a cross-cutting
   harness that re-runs several stages (5 through 11) under a frozen
   information cutoff, then hands off to Stage 14 for outcome tracking.
   **RESOLVED:** a new top-level package, `replay-engine`, was created —
   the smallest coherent change, following the same reasoning Item 1
   above already established for `evaluation-engine`. Three alternatives
   were considered and rejected:
   - **Extending `backend`** — rejected. `SYSTEM_ARCHITECTURE.md`
     Section 11 defines `backend`'s technical orchestration as routing
     requests between *live, deployed* engine services at runtime.
     Historical replay is an offline research/reconstruction harness
     that calls existing pure functions directly, in-process — no
     deployed service topology, no live request routing. Conflating the
     two would blur a genuine live-system concern with an offline tool,
     and `backend` itself remains unimplemented (placeholder only),
     unlike every engine `replay-engine` depends on.
   - **Extending `evaluation-engine`** — rejected. Stage 14 tracks
     realised outcomes against *already-produced* forecasts/
     recommendations; it has no machinery for reconstructing a
     historical information state or orchestrating the rest of the
     pipeline under a frozen cutoff. `replay-engine`'s own outcome-
     evaluation step (Part 3 of its brief) *calls* `evaluation-engine`
     directly rather than reimplementing it — the dependency runs one
     way, and folding the orchestration/snapshot half into
     `evaluation-engine` would misrepresent Stage 14's own, narrower
     documented purpose.
   - **Extending `data-engine`** — rejected. Stage 1/2's cache/vintage
     machinery (Phase E2) is directly reused for the "freeze information
     as of T" mechanism, but orchestrating the full downstream pipeline
     (causal, forecast, simulation, quant, optimisation, verification)
     is far outside `data-engine`'s Stage 1/2 boundary.

   `replay-engine` depends on `shared` plus every one of the nine
   analytical engines (it orchestrates, it does not itself perform novel
   analysis) — nothing depends back on it, so no circular package
   dependency is introduced. See `replay-engine/README.md`.
