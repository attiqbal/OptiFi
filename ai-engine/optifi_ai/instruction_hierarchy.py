"""
CIO Instruction Hierarchy — Phase E6 brief's "CIO Responsibilities" and
"CIO Prohibitions" lists, consolidated with `AI_ENGINE_SPEC.md` Section 4's
existing Never-list, each annotated with *how* it is actually enforced in
this package. `ai-engine/__init__.py` already sets the precedent this
module follows: of the Never-list's 9 items, only 4 (items 2, 3, 8, 9) were
mechanically checkable without a real LLM judging semantic content, and
only those got runtime guardrails — the rest stayed documentation. This
phase's larger prohibition list gets the same honest treatment: enforced
where genuinely checkable, documented where not, never silently assumed.

CIO RESPONSIBILITIES (Phase E6 brief) -> where implemented:
  1. interpret user intent            -> intent.classify_required_engines
  2. determine necessary specialists  -> intent.classify_required_engines
  3. inspect required dependencies    -> roadblock.detect_missing_dependencies
  4. request analysis                 -> orchestrator.CIOOrchestrator (calls
                                          real specialist functions directly)
  5. identify stale information       -> roadblock.check_staleness
  6. detect missing information       -> roadblock.detect_missing_dependencies
  7. recognise disagreement           -> disagreement.py (existing, reused)
  8. request recalculation            -> verification_gate.CIOVerdictHandling.REVISE
  9. send material recs to verification -> orchestrator calls
                                          optifi_verification directly before synthesis
  10. synthesise verified evidence    -> disagreement.synthesize_with_disagreement_preserved
                                          + framing.frame_candidate (existing, reused)
  11. explain facts/estimates/judgements/uncertainty/alternatives
                                       -> explanation.build_explanation /
                                          present_for_sophistication

CIO PROHIBITIONS (Phase E6 brief) -> enforcement:
  - invent prices/fundamentals        -> STRUCTURAL: every function in this
                                          package takes pre-built UAPs from
                                          real engine output; none accepts a
                                          raw float to synthesise a
                                          MarketObservation/FundamentalObservation.
  - calculate portfolio risk itself   -> STRUCTURAL: no risk/variance/VaR
                                          arithmetic exists anywhere in
                                          optifi_ai; quant-engine's own
                                          functions are called, never reimplemented.
  - calculate optimisation itself     -> STRUCTURAL: same — optimisation-engine's
                                          functions are called, never reimplemented.
  - construct forecast ensembles      -> STRUCTURAL: forecast-engine's own
                                          ensemble functions are called, never
                                          reimplemented here.
  - suppress model disagreement       -> ENFORCED: disagreement.py preserves
                                          every disagreeing member in
                                          `dependencies` by construction (existing).
  - convert PROVISIONAL into VERIFIED -> ENFORCED: every UAP this package
                                          constructs (frame_candidate,
                                          synthesize_with_disagreement_preserved,
                                          explain_with_disclosure — existing)
                                          hard-codes a non-VERIFIED status.
  - invent a causal relationship      -> STRUCTURAL: no CausalClaim
                                          construction exists in optifi_ai;
                                          causal-engine's own claims are consumed only.
  - alter optimisation numbers / change scenario results
                                       -> ENFORCED: frame_candidate never
                                          passes candidate.result to the
                                          generator (existing); orchestrator
                                          never mutates a specialist UAP's
                                          `.result` field.
  - invent the Capital Efficiency Score -> STRUCTURAL: quant-engine's
                                          `composite_capital_efficiency_score`
                                          is called, never reimplemented.
  - create a recommendation unsupported by authorised candidates
                                       -> ENFORCED: explanation.build_explanation's
                                          `_suggested_action` only ever names an
                                          upstream candidate's own `subject`;
                                          orchestrator raises if asked to
                                          synthesise with zero surviving candidates.
  - hide failed dependencies           -> ENFORCED: roadblock.py surfaces every
                                          missing/stale dependency; verification_gate
                                          excludes REJECTed candidates rather than
                                          silently dropping the fact that they existed
                                          (GateResult.reasons preserves why).

Documented-only (matches AI_ENGINE_SPEC.md Never-list items 1, 5, 6, 7 —
not mechanically checkable without a real LLM judging generated text):
no directive investment language (explanation.py adds one narrow, best-
effort literal-pattern guard, not a semantic guarantee); no execution
surface (structurally true — this package has no order/trade type at
all, nothing to check); no personalised Tier 3 structuring content
(HEDGING_SPEC.md/MVP_ROADMAP.md Gate B territory, out of scope for this
package entirely).
"""
