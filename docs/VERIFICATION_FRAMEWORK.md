# VERIFICATION_FRAMEWORK

**Status:** DRAFT (v1.1 — Phase 8, patch: Section 9 item 4 follow-up closed)

## 1. Purpose & Scope

This document specifies `verification-engine`'s Stage 11 role: what it
checks, how it renders a verdict, and how that verdict affects downstream
`validation_status`. It has been referenced constantly since Phase 1A as the
gate before CIO synthesis and never actually defined — this closes that gap.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 11. Consistent with
`QUANT_ENGINE_SPEC.md` Section 9's distinction between an engine's own
internal pre-check and `verification-engine`'s independent check.
Enforces `AI_ENGINE_SPEC.md` Section 4's constraints directly — see
Section 6 below. Partially resolves `ANALYTICAL_CONTRACT_SPEC.md` Section 9,
item 4 — see Section 7.

## 3. Core Principle: Independence Requirement

A verification step that re-runs the same check the originating engine
already performed is not verification — it's an echo. `verification-engine`
must apply genuinely independent methods:

- **Cross-engine consistency** — does a `JUDGEMENT`'s `provenance_chain`
  actually trace back to the `FACT`/`ESTIMATE` it claims to cite?
- **Alternate-method re-derivation**, where feasible — recomputing a simple
  result via a different path than the originating engine used.
- **Independent sourcing** — cross-referencing a claim against a source
  other than the one it originally came from, not re-checking the same
  source.
- **Present-time freshness** — checking staleness against the actual
  current time, regardless of what the originating engine asserted.
- **Corroboration audit** — confirming a `PROVISIONAL` fact was actually
  corroborated per `ANALYTICAL_CONTRACT_SPEC.md` Section 4a's rules, not
  silently treated as `VERIFIED` without it.

If `verification-engine` cannot independently check something, that itself
is worth surfacing (see Section 5.7), not silently passed.

## 4. The Verdict Taxonomy

Four verdicts, each mapped to a `validation_status` effect on the output
being checked — the verdict is metadata attached to existing output, never
a new information class (`ENGINE_PIPELINE_SPECIFICATION.md`, Stage 11):

- **PASS** — independent checks confirm the output; `validation_status`
  may move toward `VERIFIED` where applicable.
- **PASS WITH CAUTION** — output stands, but a caveat is attached (e.g. a
  dependency was itself only `PROVISIONAL`); `validation_status` is
  unchanged, but the caution note must be visible downstream, including in
  the "Why?" drill-down (`APP_UX_BLUEPRINT.md`, Section 12).
- **FLAG** — an inconsistency was found (contradicts another output,
  staleness detected, corroboration missing); `validation_status` becomes
  `CONFLICTED`, `STALE`, or `INCOMPLETE` as appropriate to the specific
  issue found.
- **REJECT** — the output fails independent verification;
  `validation_status` becomes `REJECTED` — see Section 8.

## 5. What Verification Checks For

**5.1 Evidence validation** — does the cited evidence exist and
substantively support the claim, not just formally accompany it?

**5.2 Data freshness** — is `generated_at`/`evidence_as_of` within a
reasonable window for the claim's context, checked against present time?

**5.3 Model verification** — for `ESTIMATE` output, are stated assumptions,
limitations, and confidence internally consistent with each other?

**5.4 Contradiction detection** — does this output conflict with another
`VERIFIED` or high-confidence output currently in scope? Ties directly to
`CONFLICTED` status and `disagreement_set_ref` grouping
(`ANALYTICAL_CONTRACT_SPEC.md`, Section 7).

**5.5 Recommendation review** — for Stage 10 candidates specifically,
independently re-derive whether the candidate actually respects the
constraints it claims to, rather than trusting `optimisation-engine`'s own
"Constraints: PASS" self-report from Stage 9b.

**5.6 Auditability** — can the output's full `provenance_chain` actually be
traced to real, resolvable sources? See Section 7.

**5.7 Failure classification** — when something fails, classify *why*
(data quality, model disagreement, staleness, missing dependency,
unverifiable provenance) so a `FLAG` or `REJECT` is actionable, not a
generic rejection.

## 6. Verifying `ai-engine` Specifically — Enforcing the "Never" List

Stage 11 sits between Stage 10 (`ai-engine`'s candidate framing) and Stage
12 (CIO synthesis) — meaning `verification-engine` checks `ai-engine`'s own
output too, not only the deterministic engines upstream of it. Concretely:
`verification-engine` confirms Stage 10's candidate framing has not altered
the financial figures produced by Stage 9a — directly checking compliance
with `AI_ENGINE_SPEC.md` Section 4, item 2. This makes Section 11 a real
enforcement mechanism for `ai-engine`'s constraints, not just a description
of them living in a separate document.

## 7. Resolving an Open Question: `provenance_chain` Non-Circularity

`ANALYTICAL_CONTRACT_SPEC.md` Section 9, item 4 asked who validates that
`provenance_chain` references are non-circular and actually resolvable —
`verification-engine`, or a cross-cutting infrastructure concern. **Resolved
here: `verification-engine`, consistent with its auditability role
(Section 5.6).** A follow-up patch to `ANALYTICAL_CONTRACT_SPEC.md` marking
this resolved is needed and not performed in this task.

## 8. What Happens on `REJECT`

Per `ANALYTICAL_CONTRACT_SPEC.md`'s existing `REJECTED` definition, a
rejected output must not be used downstream without an explicit, logged
override. Concretely: the CIO (`ai-engine`, Stage 12) must omit a `REJECT`ed
output from its synthesis entirely, unless an explicit override exists — and
if one does, the override itself must be logged and auditable, not a silent
bypass. This is the practical meaning of `AI_ENGINE_SPEC.md`'s "does
verification pass?" step in the CIO's reasoning sequence: a `REJECT` means
the answer is no.

## 9. Known Gaps / Open Questions

1. Exact thresholds for what separates `PASS` from `PASS WITH CAUTION` from
   `FLAG` (e.g. how much staleness is tolerable before a `FLAG`) are
   deliberately not fixed — calibration against real use is a later step.
2. Who owns and governs the "explicit, logged override" mechanism for
   `REJECTED` outputs (Section 8) is not decided.
3. Whether `verification-engine` itself needs a secondary meta-check — who
   verifies the verifier — is a genuine open question, not addressed here.
4. ~~A follow-up patch to `ANALYTICAL_CONTRACT_SPEC.md` Section 9, item
   4...~~ **RESOLVED:** that patch was completed —
   `ANALYTICAL_CONTRACT_SPEC.md` Section 9, item 4 now cites this
   document's Section 7 as the resolution.
