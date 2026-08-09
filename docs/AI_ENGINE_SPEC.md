# AI_ENGINE_SPEC

**Status:** DRAFT (v1.1 — Phase 6, patch: Section 5 item 3 resolved for checkable subset)

## 1. Purpose & Scope

`ai-engine` is the only engine that touches natural language and the only
one with any latitude for judgement. That combination is exactly why its
behavior has more accumulated constraints on it than any other engine, and
why they needed consolidating. This document defines what `ai-engine` does
at each pipeline stage it owns, and — more importantly — what it must never
do, pulling every existing rule into one place.

## 2. Relationship to Prior Documents

This document is pure synthesis. Every rule below is sourced from:
`ENGINE_PIPELINE_SPECIFICATION.md` (Stages 3, 10, 12, 13; Section 7
multi-model disagreement; Section 11 orchestration distinction),
`ANALYTICAL_CONTRACT_SPEC.md` (the UAP contract; Section 4a corroboration
ownership), `PRODUCT_VISION.md` (Section 9 CIO philosophy; Section 11a
Capital Efficiency Score), `MVP_ROADMAP.md` (Gate B, Gate C), and
`APP_UX_BLUEPRINT.md` (Section 3 standing UI constraints; Section 6 Gate B
wording contrast; Section 12 the "Why?" pattern). No rule here originates in
this document.

## 3. The Four Stages `ai-engine` Owns

### 3.1 Stage 3 — Unstructured Extraction Support
`ai-engine` assists `data-engine` in extracting structured claims from
unstructured text (news, filings prose). Output is always
`information_class: FACT` — extraction identifies a claim, it does not
analyse one, so it is never `ESTIMATE` or `JUDGEMENT`. Output carries
`validation_status: PROVISIONAL` by default. **`ai-engine` does not
self-certify its own extraction as `VERIFIED`** — corroboration is
`data-engine`'s call (`ANALYTICAL_CONTRACT_SPEC.md`, Section 4a), not
`ai-engine`'s to grant itself.

### 3.2 Stage 10 — Candidate Framing & Explanation
`ai-engine` explains and contextualises candidates that `optimisation-engine`
already produced and policy-validated (Stages 9a/9b). **Hard constraint:
`ai-engine` must not invent, alter, or substitute a different financial
action, or change a candidate's quantitative figures.** It may rank,
compare, and narrate. Output is `JUDGEMENT`, and every figure it cites must
remain traceable, unmodified, to the `ESTIMATE` it came from.

### 3.3 Stage 12 — CIO / Manager Synthesis
Reasoning sequence (`PRODUCT_VISION.md`, Section 9): what does the user want
to know → which specialists are needed → is their information current → do
their conclusions agree → is anything missing → does verification pass →
only then, what to tell the user. **Hard constraints:**
- Must not mathematically resolve disagreement between multiple `ESTIMATE`
  entries sharing a `subject` (`ENGINE_PIPELINE_SPECIFICATION.md`,
  Section 7) — it explains disagreement, it does not pick or average a
  winner.
- Must not invent or assert the Capital Efficiency Score, or any other
  figure owned by a specialist engine's computation — it explains a
  computed figure, it does not produce one (`PRODUCT_VISION.md`,
  Section 11a).
- This is *analytical* orchestration, distinct from `backend`'s *technical*
  orchestration (`ENGINE_PIPELINE_SPECIFICATION.md`, Section 11) — `ai-engine`
  decides which specialists to consult and whether they agree; it does not
  route data between services.

### 3.4 Stage 13 — User-Facing Explanation
Must preserve `information_class` and `validation_status` distinctions in
whatever it generates — never flattened into undifferentiated prose. A
non-`VERIFIED` item reaching the user must say so.

## 4. The Consolidated "Never" List

Every constraint on `ai-engine` established anywhere in this project, in one
place:

1. Never perform a deterministic calculation a specialist engine should do
   (the founding principle, `ENGINE_PIPELINE_SPECIFICATION.md` Section 3).
2. Never invent, alter, or substitute a different financial action than
   what `optimisation-engine` produced (Section 3.2 above).
3. Never mathematically resolve multi-model disagreement — explain it
   instead (Section 3.3 above).
4. Never invent or assert the Capital Efficiency Score, or any other
   specialist-owned computed figure (Section 3.3 above).
5. Never use directive investment language — no "Buy X," no "Sell X"
   (`APP_UX_BLUEPRINT.md`, Section 3).
6. Never present a transaction or execution control of any kind — this MVP
   has no execution surface (`MVP_ROADMAP.md`, Gate C).
7. Never present a personalised Tier 3 structure or a specific £ figure
   tied to the user's own numbers for estate/trust planning — flag-only,
   generic, per the safe/unsafe contrast in `APP_UX_BLUEPRINT.md`,
   Section 6, and gated regardless (`MVP_ROADMAP.md`, Gate B).
8. Never self-certify its own Stage 3 extraction as `VERIFIED` (Section 3.1
   above).
9. Never present a non-`VERIFIED` item to the user without flagging its
   `validation_status` (Section 3.4 above).

## 5. Known Gaps / Open Questions

1. Exact UX for surfacing `validation_status` to users (default-visible vs.
   on-demand via "Why?") is still open per `APP_UX_BLUEPRINT.md` Section 17,
   item 2 — this document doesn't resolve it either.
2. The technical handoff between `ai-engine`'s Stage 3 extraction output and
   `data-engine`'s corroboration process is not specified — only that
   `data-engine` owns the decision.
3. ~~Whether the Section 4 "Never" list should become a literal runtime
   guardrail...~~ **RESOLVED (partially):** implemented as runtime
   guardrails for items 2, 3, 8, and 9 — see `ai-engine`'s
   `frame_candidate`, `synthesize_with_disagreement_preserved`,
   `extract_structured_claim`, and `explain_with_disclosure`, plus
   `verification-engine`'s `verify_candidate_framing_unaltered`. Items
   1, 4, 5, 6, and 7 remain design-specification-only, not yet
   runtime-enforced.
