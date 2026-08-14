# CIO_ORCHESTRATION_SPEC

**Status:** DRAFT (v1 — Phase E6)

## 1. Purpose & Scope

This document specifies the CIO/Manager orchestration layer added in Phase
E6: `ai-engine`'s `intent.py`, `roadblock.py`, `verification_gate.py`,
`evidence_trace.py`, `explanation.py`, `orchestrator.py`, and
`instruction_hierarchy.py`. It covers dynamic routing, roadblock
management, the verification gate, the "Why?" evidence trace,
sophistication-tiered explanation, the instruction hierarchy, and the LLM
provider boundary — Stage 12/13 of `ENGINE_PIPELINE_SPECIFICATION.md`.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 12 ("CIO / Manager
Synthesis") and Stage 13 ("User-Facing Explanation"), and Section 11's
analytical/technical orchestration distinction. Builds directly on
`AI_ENGINE_SPEC.md` (whose Never-list this document's
`instruction_hierarchy.py` consolidates against Phase E6's own
Responsibilities/Prohibitions list) and `VERIFICATION_FRAMEWORK.md`
(whose four-value `VerdictType` this layer maps, not replaces). Consistent
with `PRODUCT_VISION.md` Section 9's CIO reasoning sequence and Section 10's
information-trust philosophy.

## 3. Architecture

The CIO is *analytical* orchestration, not *technical* orchestration
(`ENGINE_PIPELINE_SPECIFICATION.md` Section 11) — it decides which
specialists a query needs and reasons across their outputs; it does not
route requests between live services, because no live service layer exists
yet (`backend` remains a placeholder, README.md). Concretely, every
specialist "call" in this phase is a direct, in-process Python function
call — the same pattern `replay-engine` (Phase E5) already established,
since nothing in this repository is a network service.

`SpecialistOutputPool` (`orchestrator.py`) stands in for whatever a future
`backend` would eventually assemble by calling specialist engine services.
The CIO consumes a pool; it never produces a FACT or ESTIMATE UAP of its
own to put into one.

**Import boundary.** Before Phase E6, `ai-engine` depended only on
`optifi_shared`. `orchestrator.py` now depends on `optifi_causal`,
`optifi_forecast`, `optifi_simulation`, `optifi_optimisation`, and
`optifi_verification` to call real specialist functions for its worked
examples; `verification_gate.py` and `explanation.py` depend on
`optifi_verification` alone. `verification-engine` already depends on
`ai-engine` (for `frame_candidate`, to verify its own Stage 10 output) —
re-exporting the heavy CIO modules from `ai-engine/optifi_ai/__init__.py`
would have made that existing dependency pull in five more packages just
to import `optifi_ai` at all, a one-way pipeline dependency turning into a
practical installation cycle. `optifi_ai/__init__.py` therefore keeps
re-exporting only its pre-existing, `optifi_shared`-only-dependent
surface (plus the equally lightweight `intent.py`/`roadblock.py`); the
heavier modules are fully real and tested, just imported directly
(`from optifi_ai.orchestrator import CIOOrchestrator`) by whoever wants
the CIO layer specifically.

## 4. Dynamic Routing

`intent.classify_required_engines(query_text)` decides which
`SpecialistEngine`s a query needs, so the CIO does not run every engine for
every request. This is a **deterministic keyword heuristic, not a real
LLM/NLU call** — `StubExplanationGenerator` cannot genuinely understand
intent (see `ai-engine/generator.py`), so implementing routing as a call to
`.generate()` and trusting its output would be exactly the kind of
fabrication CLAUDE.md forbids. The heuristic is honest about what it is:
its `RoutingDecision.is_heuristic` is always `True`, and its `reasoning`
list names which keywords matched.

Two thresholds anchor the heuristic, matching the Phase E6 brief's own
examples: plain lookup language routes a single specialist (e.g.
"allocation" -> `QUANT` only); decision language ("should I", "because",
"recession", "reduce", ...) routes the full chain (`CAUSAL -> FORECAST ->
SIMULATION -> QUANT -> OPTIMISATION -> VERIFICATION`). `VERIFICATION` is
always added whenever `OPTIMISATION` is routed.

## 5. Roadblock Management

`roadblock.py` detects — never silently resolves — two kinds of gap:

- **Missing dependency**: a `SpecialistEngine` the routing decision
  requires has no output in the pool at all.
- **Stale data**: a UAP's `evidence_as_of`/`observation_time`/
  `generated_at` is older than a caller-supplied `max_age`, checked against
  present time (`VERIFICATION_FRAMEWORK.md` Section 5.2).

No "request refresh" capability is implemented: `data-engine` has no live
vendor connected, so there is nothing to genuinely refresh yet (see Section
8, item 2). A roadblock can only be surfaced to the caller, which is what
`explanation.py`'s `roadblocks` field and `suggested_action` qualification
do — never fabricate a substitute, never proceed as if the gap didn't
exist.

## 6. Verification Gate

Phase E6 asks the CIO to handle five categories: `PASS`, `PASS WITH
CAUTION`, `REVISE`, `INSUFFICIENT EVIDENCE`, `REJECT`. `verification-engine`'s
actual, tested `VerdictType` has four (`PASS`, `PASS WITH CAUTION`, `FLAG`,
`REJECT`; `FLAG` sub-typed by `flagged_status` in `{CONFLICTED, STALE,
INCOMPLETE}`). Rather than changing that already-implemented engine,
`verification_gate.py` maps onto it:

| `VerdictType` | `flagged_status` | CIO handling |
|---|---|---|
| `PASS` | — | `PASS` |
| `PASS WITH CAUTION` | — | `PASS_WITH_CAUTION` |
| `FLAG` | `CONFLICTED` or `STALE` | `REVISE` (recalculation is meaningful) |
| `FLAG` | `INCOMPLETE` | `INSUFFICIENT_EVIDENCE` |
| `REJECT` | — | `REJECT` |

When several verdicts apply to one candidate, `apply_gate` takes the single
worst handling (`REJECT` > `INSUFFICIENT_EVIDENCE` > `REVISE` > `PASS WITH
CAUTION` > `PASS`), mirroring `shared`'s `worst_validation_status`
convention. Only `REJECT` excludes a candidate from CIO synthesis entirely
(`excluded=True`) — per `VERIFICATION_FRAMEWORK.md` Section 8, the CIO
cannot override it. No override mechanism exists in this phase; Section 9,
item 2 of that document leaves override governance undecided, and inventing
one here would silently resolve an open question rather than carry it
forward (see Section 8 below).

## 7. Explanation Structure & Evidence Trace

`explanation.build_explanation` assembles the Phase E6 structure
deterministically from real UAPs — `information_class` already says whether
something is FACT/ESTIMATE/JUDGEMENT, so no generator call decides the
bucketing. `present_for_sophistication` is the only place a generator
produces prose, and it only varies narrative depth
(`UserSophistication.BEGINNER/INFORMED/PROFESSIONAL`); the underlying
`CIOExplanation` — including `suggested_action`, which is always `"NO
ACTION"` unless a real, non-excluded candidate survived the gate — is
identical across tiers, per `PRODUCT_VISION.md` Section 10.

`evidence_trace.trace_evidence` is the "Why?" pathway
(`APP_UX_BLUEPRINT.md` Section 12), reusing `disclosure.py`'s existing,
already-tested dependency/provenance walk rather than a second
implementation.

## 8. Known Gaps / Open Questions

1. **Intent classification is a heuristic, not real NLU.** A genuine
   limitation until a real LLM/NLU provider is wired — see Section 9.
2. **No live "request refresh" capability exists.** `data-engine` has no
   live vendor connected (README.md); roadblock handling can only defer or
   qualify a conclusion, never actually fetch something newer.
3. **`REJECTED`-override governance remains undecided.**
   `VERIFICATION_FRAMEWORK.md` Section 9, item 2 already leaves this open;
   this phase implements no override path at all rather than inventing
   governance for it.
4. **Staleness thresholds remain uncalibrated by design.**
   `VERIFICATION_FRAMEWORK.md` Section 9, item 1 deliberately leaves this
   open; `check_staleness` requires callers to supply `max_age` explicitly
   rather than this phase picking a number.
5. **Exact sophistication-tier UX remains open.** `APP_UX_BLUEPRINT.md`
   Section 17, item 2 is unresolved; this phase's three-tier text-depth
   split is an implementation-level default, not a resolution of that
   product question.
6. **The directive-language guard is a literal-pattern heuristic, not a
   semantic guarantee.** It catches the exact phrasing
   `AI_ENGINE_SPEC.md` Section 4 item 5 names as its own example
   ("Buy X"), nothing broader — genuine enforcement requires a real LLM
   judging generated text's meaning, which this phase does not build.
7. **Dynamic routing operates on already-populated pools, not live
   service calls.** `SpecialistOutputPool` is filled by direct in-process
   function calls in this phase's tests and worked examples; a real
   `backend` service layer that actually dispatches requests to running
   specialist services at runtime is unbuilt and out of scope
   (`ENGINE_PIPELINE_SPECIFICATION.md` Section 11).

## 9. LLM Provider Boundary

Unchanged from `ai-engine`'s existing design: every function that produces
natural language takes an `ExplanationGenerator`
(`generate(prompt, context) -> str`); the only implementation is
`StubExplanationGenerator`. No function anywhere in this package — including
everything added in Phase E6 — calls a real LLM provider, holds an API key,
or makes a network request. Swapping in a real provider means writing one
new class satisfying that Protocol; no orchestration, routing, roadblock, or
verification-gate code changes. Nothing in `optifi_ai`'s control flow or
routing decisions depends on hidden conversational memory — the pool, the
routing decision, and every UAP the CIO reasons over are structured
`shared/optifi_shared` objects, not opaque model state.
