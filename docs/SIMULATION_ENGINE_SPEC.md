# SIMULATION_ENGINE_SPEC

**Status:** DRAFT (v1.1 — Phase 13, patch: Section 10 items 2 and 3 follow-ups closed)

## 1. Purpose & Scope

This document specifies `simulation-engine`'s Stage 7 output and, most
importantly, clarifies exactly where its work ends and `quant-engine`'s
Stage 8 work begins — a boundary previous documents described loosely
enough to blur together.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 7, which consumes
`causal-engine`'s Stage 5 relationships and `forecast-engine`'s Stage 6
outputs. `APP_UX_BLUEPRINT.md` Section 10's Scenario Lab example attributes
scenario propagation and portfolio evaluation to "OptiFi" generically —
Section 3 below assigns that work precisely between two engines.

## 3. Clarifying the Stage 7 / Stage 8 Boundary

This is the key architectural clarification in this document:

- **`simulation-engine` (Stage 7)** propagates a scenario through markets
  and the economy, producing scenario-conditional effects at the
  asset-class or sector level — general, not tied to any specific user
  (e.g. "under a 100bp rate cut, UK Gilts +X%, Bank equities -Y%,
  Property +Z%").
- **`quant-engine` (Stage 8)** applies that general, scenario-conditional
  output to a specific user's actual portfolio composition, producing the
  personalised portfolio-level impact figure (e.g. the "+2.8%" a user
  actually sees).

`APP_UX_BLUEPRINT.md`'s Scenario Lab example blends both steps into one
user-facing flow, which is fine as UX language — but the underlying engine
division of labour is now precise: `simulation-engine` never touches a
specific user's holdings.

## 4. Confirming the `SECURITY.md` Assumption

Given Section 3's clarification, `simulation-engine` operates on general
market/economic scenario propagation and does not need raw per-user
Financial Twin access — the personalisation step belongs entirely to
`quant-engine`, which `SECURITY.md` Section 5 already correctly identified
as needing that access. **This completes `SECURITY.md` Section 11, item 2**
— `causal-engine`, `forecast-engine`, and now `simulation-engine` are all
confirmed. A follow-up patch is needed and not performed here.

## 5. Scenario Definition

A scenario is a perturbation to one or more `ECONOMIC_ONTOLOGY.md` entities
or economic variables (e.g. "UK base rate: -100bp"). **Recommendation for
MVP: preset-only scenarios, not free-form.** Reasoning: free-form scenario
construction requires interpreting an arbitrary natural-language "what if"
query into a valid, well-formed perturbation — a substantially harder,
more open-ended problem than propagating a curated, pre-vetted scenario
already mapped to valid Ontology entities. This is a recommendation, not a
mandate — it directly informs (but does not itself resolve) the open
question in `APP_UX_BLUEPRINT.md` Section 17, item 5. A follow-up patch
there is needed and not performed here.

## 6. Scenario Propagation

Propagation uses `causal-engine`'s Stage 5 relationships as the pathways a
perturbation travels along, combined with `forecast-engine`'s Stage 6
baseline forecasts where relevant. The specific propagation algorithm is
deliberately not specified — it inherits `causal-engine`'s
methodology-agnosticism (`CAUSAL_ENGINE_SPEC.md`, Section 3) rather than
independently choosing a different level of specificity.

## 7. Output: Asset-Class / Sector-Level Impact

Per Section 3, `simulation-engine`'s output is scenario-conditional
impact at the asset-class or sector level — `information_class: ESTIMATE`,
scenario-conditional (`ENGINE_PIPELINE_SPECIFICATION.md`, Stage 7). This is
what `quant-engine` consumes for Stage 8's personalised impact
calculation — not a portfolio-level figure in its own right.

## 8. Uncertainty & Sensitivity Analysis

Consistent with the "plausible futures, not predictions" principle
(`PRODUCT_VISION.md`, Section 11), every simulation output carries a base
case plus a range, not a single value. Sensitivity analysis identifies
which input assumptions the outcome depends on most heavily (e.g. "outcome
is highly sensitive to GBP response," matching the existing "Key
uncertainty" pattern in `APP_UX_BLUEPRINT.md` Section 10).

## 9. Multi-Pathway Disagreement

Where multiple causal pathways or forecast inputs feeding a scenario
disagree, this follows the existing disagreement-preservation principle
(`ANALYTICAL_CONTRACT_SPEC.md`, Section 7) — not a new rule specific to
this engine.

## 10. Known Gaps / Open Questions

1. The specific propagation algorithm (Section 6) is not specified —
   inherited openness from `CAUSAL_ENGINE_SPEC.md`, not a gap unique to
   this document.
2. ~~Section 5's preset-only recommendation is not binding...~~
   **RESOLVED:** that patch was completed — `APP_UX_BLUEPRINT.md`
   Section 17, item 5 now cites this document's Section 5 as the
   resolution.
3. ~~A follow-up patch to `SECURITY.md` completing Section 11, item
   2...~~ **RESOLVED:** that patch was completed — `SECURITY.md`
   Section 11, item 2 now cites this document's Section 4 as completing
   the three-engine confirmation.
4. Whether `simulation-engine`'s asset-class-level output granularity is
   sufficient for `quant-engine`'s actual Stage 8 needs is not verified
   against implementation.
