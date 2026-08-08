# CAUSAL_ENGINE_SPEC

**Status:** DRAFT (v1.1 — Phase 11, patch: Section 8 item 3 follow-up closed)

## 1. Purpose & Scope

This document specifies `causal-engine`'s Stage 5 output contract and the
principles governing what counts as an acceptable causal claim. It does not
choose how causal relationships are computed — see Section 3.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 5, and Stage 4's joint
ownership with `data-engine`. Causal claims reference entities defined in
`ECONOMIC_ONTOLOGY.md` by identifier, per that document's Section 6 — not as
free text. Confirms the assumption left open in `SECURITY.md` Section 5 and
Section 11, item 2 — see Section 4 below.

## 3. Why This Document Stays Methodology-Agnostic

Portfolio and risk mathematics (`QUANT_ENGINE_SPEC.md`) is settled —
there's no real debate about what a Sharpe ratio is. Causal inference is
not settled in the same way: structural causal models, Granger-style
precedence tests, instrumental variables, natural experiments, and DAG-based
approaches all make different assumptions and fail differently, and
choosing among them has real consequences for whether the resulting claims
are valid. This document specifies the contract a causal claim must satisfy
regardless of method — it deliberately does not pick a method.

## 4. Confirming the `SECURITY.md` Assumption

`SECURITY.md` Section 5 assumed `causal-engine` rarely needs raw per-user
Financial Twin access, since its work is primarily over the shared,
non-personal `ECONOMIC_ONTOLOGY.md`, producing general claims (e.g. "rate
cuts influence mortgage refinancing rates") rather than user-specific ones.
**Confirmed here:** `causal-engine` operates on shared entities and
produces general-purpose causal claims; applying a causal claim to a
specific user's portfolio happens downstream, in `quant-engine` or
`simulation-engine`, not in `causal-engine` itself. A follow-up patch to
`SECURITY.md` marking Section 11, item 2 resolved is needed and not
performed here.

## 5. Causal Claim Requirements

**5.1 Causal representation** — a claim expresses a relationship between
two or more `ECONOMIC_ONTOLOGY.md` entities, with a stated direction and a
described transmission mechanism — not merely "X and Y move together."

**5.2 Evidence requirements — the correlation/causation guardrail.** A
causal claim requires at least one of: (a) a plausible, explicitly stated
economic mechanism connecting cause to effect, or (b) historical precedent
— the relationship has held across multiple prior instances, not just the
current observation. **Bare statistical correlation, with neither a stated
mechanism nor historical precedent, must never be output as a causal
claim.** Where only correlation is available, `causal-engine` either
declines to produce a causal claim, or produces a `JUDGEMENT` explicitly
noting an unconfirmed causal direction — never an assertion of causation.
This is a hard rule, not a preference — see Section 6.

**5.3 Relationship strength** — where possible, claims express magnitude,
not only direction (e.g. an approximate expected effect size), not just
"X influences Y."

**5.4 Time lag** — transmission mechanisms often operate with delay; a
claim should state the expected lag between cause and effect where known,
since `forecast-engine` and `simulation-engine` depend on this to sequence
their own outputs correctly.

**5.5 Confidence** — every claim carries `information_class: ESTIMATE`
and a `confidence` value reflecting the strength of evidence under 5.2 — a
claim resting only on a plausible mechanism with little precedent carries
lower confidence than one with a strong track record.

**5.6 Causal validation** — before use downstream, a claim is checked for
basic validity: does the claimed direction make economic sense, is the
timeline internally consistent, does the relationship still hold given
current data rather than being broken by a structural change in the
economy? This is `causal-engine`'s own internal check, distinct from
`verification-engine`'s independent Stage 11 re-check
(`VERIFICATION_FRAMEWORK.md`, Section 3).

**5.7 Uncertainty** — key limitations (e.g. "may not hold during unusually
high inflation") belong in the `limitations` field, not omitted.

## 6. The Correlation/Causation Guardrail, Restated

This is important enough to state on its own, not only buried in Section
5.2: `causal-engine`'s output must never present correlation as causation.
Given that Stage 3's unstructured extraction and Stage 12's CIO synthesis
both involve LLM interpretation elsewhere in this pipeline, and LLMs are
well known to blur this exact distinction, this rule is a structural
safeguard, not a stylistic preference. A causal-sounding claim without real
grounding can mislead a user about *why* something is happening, which has
real consequences for how they'd read a scenario or a recommendation.

## 7. Multi-Model Disagreement

Where competing causal claims disagree about a relationship (one asserts a
strong effect, another a weak or absent one), they are preserved as a
plural set sharing one `subject`, per `ANALYTICAL_CONTRACT_SPEC.md`
Section 7 — not collapsed into a single claim before reaching `ai-engine`.

## 8. Known Gaps / Open Questions

1. The specific causal inference methodology is deliberately not chosen
   here — this is a genuine, contested decision requiring dedicated
   deliberation, unlike the settled formulas in `QUANT_ENGINE_SPEC.md`.
2. Exact thresholds for "sufficient historical precedent" (Section 5.2) are
   not defined.
3. ~~A follow-up patch to `SECURITY.md` marking Section 11, item 2
   resolved...~~ **RESOLVED:** that patch was completed — `SECURITY.md`
   Section 11, item 2 now cites this document's Section 4 (alongside
   `FORECAST_ENGINE_SPEC.md` and `SIMULATION_ENGINE_SPEC.md`) as fully
   confirming the assumption.
4. Whether `causal-engine` ever needs limited access to aggregated,
   non-identifiable portfolio-pattern data (distinct from raw per-user Twin
   access) to detect emerging relationships is not addressed.
