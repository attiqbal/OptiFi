# SIMULATION_ENGINE_SPEC

**Status:** DRAFT (v1.2 — Phase E4, patch: Sections 5/6/7/8 given a first concrete implementation)

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

**Implemented (Phase E4):** `scenario_library.py`'s `ScenarioDefinition`
+ `SCENARIO_LIBRARY` — exactly the preset-only shape this section
recommends, seven curated presets (one per named category in the Phase
E4 brief: rates, inflation, recession, equity shock, FX, commodity,
earnings), not a free-form authoring surface.

## 6. Scenario Propagation

Propagation uses `causal-engine`'s Stage 5 relationships as the pathways a
perturbation travels along, combined with `forecast-engine`'s Stage 6
baseline forecasts where relevant. The specific propagation algorithm is
deliberately not specified — it inherits `causal-engine`'s
methodology-agnosticism (`CAUSAL_ENGINE_SPEC.md`, Section 3) rather than
independently choosing a different level of specificity.

**A first concrete implementation exists (Phase E4):**
`propagation.py`'s `propagate_scenario` — requires a supported causal
pathway (`causal-engine`'s `TransmissionGraph`) from the scenario's
perturbed entity to the target asset, and a registered
empirical/deterministic sensitivity (`quant-engine`'s
`factor_sensitivity.py`/`SensitivityRegistry`) quantifying it, then
computes `base_case`/`range` genuinely from that sensitivity — no
hand-authored numbers. This is presented as A defensible first
implementation, not THE definitive algorithm this section's own
open-endedness anticipated — see the Phase E4 deliverable's own
"unresolved research questions" for what it does not attempt (composing
sensitivities across multiple pathway hops; a non-linear/general-
equilibrium propagation model).

## 7. Output: Asset-Class / Sector-Level Impact

Per Section 3, `simulation-engine`'s output is scenario-conditional
impact at the asset-class or sector level — `information_class: ESTIMATE`,
scenario-conditional (`ENGINE_PIPELINE_SPECIFICATION.md`, Stage 7). This is
what `quant-engine` consumes for Stage 8's personalised impact
calculation — not a portfolio-level figure in its own right.

**Implemented (Phase E4):** `quant-engine`'s `propagate_to_portfolio`
(`portfolio_propagation.py`) is exactly this Stage 7 -> Stage 8 handoff,
applying `ScenarioResult`s to specific holdings/weights to produce the
personalised portfolio-level figure with per-holding attribution.

## 8. Uncertainty & Sensitivity Analysis

Consistent with the "plausible futures, not predictions" principle
(`PRODUCT_VISION.md`, Section 11), every simulation output carries a base
case plus a range, not a single value. Sensitivity analysis identifies
which input assumptions the outcome depends on most heavily (e.g. "outcome
is highly sensitive to GBP response," matching the existing "Key
uncertainty" pattern in `APP_UX_BLUEPRINT.md` Section 10).

**Strengthened (Phase E4):** `ScenarioResult`'s own guardrail (already
requiring a range to exist) now additionally requires genuine width
(`range_low < range_high`, strictly) — a zero-width range technically
satisfied the old guardrail while expressing no real uncertainty at all.
See `scenario_result.py`'s own docstring, guardrail 4.

## 9. Multi-Pathway Disagreement

Where multiple causal pathways or forecast inputs feeding a scenario
disagree, this follows the existing disagreement-preservation principle
(`ANALYTICAL_CONTRACT_SPEC.md`, Section 7) — not a new rule specific to
this engine.

## 10. Known Gaps / Open Questions

1. ~~The specific propagation algorithm (Section 6) is not specified...~~
   **PARTIALLY ADDRESSED (Phase E4):** a first concrete implementation
   exists (Section 6) — transmission-graph pathway + registered
   sensitivity, linear combination. Not marked fully RESOLVED: this is
   one defensible implementation, not a claim that harder open questions
   (multi-hop sensitivity composition, non-linear/regime-switching
   propagation, joint-distribution portfolio-level range combination —
   see the Phase E4 deliverable) are settled.
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
