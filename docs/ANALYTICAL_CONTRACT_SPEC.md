# ANALYTICAL_CONTRACT_SPEC

**Status:** DRAFT (v1.4 — Phase 1B/1C, patch: Section 9 item 2 resolved)

## 1. Purpose & Scope

Every OptiFi analytical engine must eventually communicate using a
standardised structured object called the **Universal Analytical Packet
(UAP)**. This exists to prevent specialist systems from exchanging vague,
unstructured analytical claims. A receiving engine must be able to determine,
from the packet alone:

- what the sending engine concluded
- what type of information it is
- what evidence supports it
- when the evidence was valid
- how fresh it is
- which model or process produced it
- how uncertain it is
- which assumptions were made
- which limitations apply
- which upstream dependencies were used, and whether they succeeded
- whether conflicting evidence exists
- how the conclusion traces back to original sources

> **Every important analytical output must be machine-readable, traceable,
> challengeable, and reproducible.**

This document defines the conceptual shape of that packet. It does not
define types, serialization, storage, or transport.

## 2. Relationship to Prior Documents

`ENGINE_PIPELINE_SPECIFICATION.md` (Phase 1A) introduced a minimal 10-field
UAP shape and deferred its full definition to this document. **This document
is now the authoritative definition of the UAP.** Where the two differ, this
document governs. Updating Phase 1A's Section 6 to point here instead of
maintaining its own field list is a housekeeping item — see Section 9.

## 3. Fundamental Information Model

OptiFi recognises exactly three primary information classes. This is
unchanged from Phase 1A.

### FACT
Information representing an observed or deterministically derived state
(reported CPI, a security price, reported company revenue, a verified
portfolio holding, a portfolio value calculated deterministically from
verified holdings and prices). FACT does not mean "eternally true" — a fact
may still be stale, provisional, conflicted, or incomplete. Those properties
belong to `validation_status`, never to `information_class`.

### ESTIMATE
Information produced by a model or analytical process involving uncertainty
(expected volatility, probability of recession, a GDP forecast, estimated
beta, simulated drawdown, predicted earnings growth, an estimated causal
effect). An estimate must expose its uncertainty and model context.

### JUDGEMENT
An interpretation or decision-oriented conclusion derived from FACT and/or
ESTIMATE inputs (portfolio duration exposure appears excessive; valuations
appear unattractive relative to expected growth; available evidence does not
justify action). Judgements must remain traceable to their supporting facts
and estimates.

## 4. Validation Status

Independent of information class — never conflated with it. The canonical
set, carried forward unchanged from Phase 1A v2:

- **VERIFIED** — confirmed via corroboration, or directly-sourced structured
  data with no outstanding concern.
- **PROVISIONAL** — not yet corroborated.
- **CONFLICTED** — multiple sources or models disagree and the conflict is
  unresolved.
- **STALE** — was valid but its freshness window has lapsed without a
  refresh.
- **INCOMPLETE** — partially available; missing a required field or
  dependency.
- **REJECTED** — failed validation or independent verification; must not be
  used downstream without an explicit, logged override.
- **SUPERSEDED** — was valid, and possibly `VERIFIED`, at the time, but
  has been explicitly replaced by a newer official release of the same
  underlying fact from the same source (e.g. a GDP advance estimate
  superseded by the second estimate). Distinct from `STALE` (the old
  value isn't wrong, just unrefreshed) and from `REJECTED` (which
  signals a failure in OptiFi's own validation or verification, not a
  legitimate correction from the source).

## 4a. Corroboration Requirement for PROVISIONAL Status

A `PROVISIONAL` fact becomes `VERIFIED` only through one of two mechanisms,
both requiring genuine independence — not through elapsed time and not
through repetition of the same underlying source:

1. **Independent corroboration** — the same claim is separately extracted
   from a second, distinct source that does not share a common upstream
   origin with the first (e.g. two outlets both republishing the same wire
   report or press release does **not** count).
2. **Structured cross-check** — the claim is confirmed against a directly-
   sourced `FACT` (an official filing, an official statistics release)
   covering the same underlying claim.

No new UAP field is required — corroboration is recorded by adding the
additional independent source(s) to the existing `evidence` field, at which
point `validation_status` is updated to `VERIFIED`. Corroboration-checking
is a `data-engine` responsibility (matching/deduplication and cross-
referencing against structured facts), consistent with `data-engine`
already owning Stage 3.

A `PROVISIONAL` fact that has not been corroborated is **not** automatically
reclassified as `STALE` — `STALE` describes something that was once fresher
and has lapsed; an uncorroborated claim was never `VERIFIED` to begin with,
so there is nothing to lapse from. It simply remains `PROVISIONAL`
indefinitely until corroborated, and downstream stages must continue
treating it at `PROVISIONAL` trust regardless of how long it has persisted
in that state.

## 5. The Universal Analytical Packet — Field Definitions

Every UAP carries the following. This is a conceptual field list — names and
meanings, not types, defaults, or storage format.

**Identity & classification**
- `id` — a unique identifier for this specific packet instance, so other
  packets can reference it (see `provenance_chain` below).
- `subject` — a stable identifier for the analytical question, quantity, or
  entity this packet answers (e.g. "US recession probability, 12-month
  horizon"). Necessary so that competing packets answering the same question
  can be grouped — see Section 7.
- `information_class` — `FACT` / `ESTIMATE` / `JUDGEMENT`.
- `validation_status` — as defined in Section 4.

**Content**
- `result` — the conclusion or value itself.

**Provenance & timing**
- `source` — the external evidentiary origin (a data provider, a filing, a
  publication). Distinct from `producer` below.
- `producer` — the internal OptiFi engine and methodology/model identity
  that generated this packet (e.g. "forecast-engine / econometric model").
- `evidence` — pointer(s) to or description of the supporting evidence.
- `evidence_as_of` — the point in time the underlying evidence or data
  refers to (answers "when was this valid").
- `generated_at` — when this packet itself was produced (answers "how fresh
  is it," relative to now).

**Uncertainty & reasoning**
- `confidence` — degree of certainty in the result.
- `assumptions` — assumptions made in producing the result.
- `limitations` — known limitations of methodology or scope.

**Structural relationships**
- `dependencies` — the upstream inputs this result relied on. Each
  dependency must carry its own resolution status (succeeded / degraded /
  failed) — a packet must not silently proceed as if a failed dependency
  succeeded; a critical dependency failure should be reflected in this
  packet's own `validation_status` (typically `INCOMPLETE` or `REJECTED`).
- `provenance_chain` — explicit references, by `id`, to the specific
  upstream packets this result was derived from. A directly-sourced FACT
  typically has an empty or minimal chain (traced only to an external
  `source`); an ESTIMATE or JUDGEMENT typically references the FACT/ESTIMATE
  packets that fed it.
- `disagreement_set_ref` — optional. Where this packet is one of several
  competing answers to the same `subject` (see Section 7), a reference
  linking it to its siblings.
- `supersedes` — optional. References the `id` of the earlier packet(s),
  sharing this packet's `subject`, that this packet officially replaces.
  When set, the referenced packet's `validation_status` is updated to
  `SUPERSEDED`. There is no corresponding forward-pointing field on the
  superseded packet.

## 6. Provenance & Traceability

A JUDGEMENT must be traceable, via `provenance_chain`, back through the
ESTIMATE and FACT packets that support it, ultimately terminating at
external `source` references. This is what makes a conclusion "challengeable"
in the sense required by Section 1 — anything downstream can be interrogated
back to its origin without re-running any analysis.

## 7. Multi-Model Disagreement Grouping

Phase 1A (Section 7) established that competing model outputs for the same
target must be preserved as a plural set rather than collapsed. This
document supplies the mechanism: packets sharing the same `subject` and
representing genuinely competing answers reference one another via
`disagreement_set_ref`. The CIO / Manager layer (Stage 12) retrieves the
full set for a given `subject` rather than a single packet, and explains
disagreement rather than resolving it — consistent with Phase 1A Section 7.
The governance question of who issues and controls `subject` identifiers is
not resolved here — see Section 9.

## 8. Dependency Resolution

A packet's `dependencies` are not a passive record — they gate the packet's
own trustworthiness. If a dependency an engine relied on failed or degraded,
that must be visible in this packet's own `validation_status`, not silently
absorbed by falling back to a default. A downstream consumer should never
have to inspect a chain of dependencies to discover a failure that the
packet itself could have surfaced directly.

## 9. Known Gaps / Open Questions Carried to Phase 1C

1. ~~Should `REVISED` be added as a seventh `validation_status`
   value...~~ **RESOLVED:** added `SUPERSEDED` (not `REVISED`) as the
   seventh value, paired with a new `supersedes` field. See Sections 4
   and 5.
2. ~~Should `ENGINE_PIPELINE_SPECIFICATION.md` Section 6 be updated...~~
   **RESOLVED:** completed in an earlier patch — that document's Section
   6 now explicitly defers to this document's Section 5.
3. What governs `subject` identifiers — a controlled vocabulary, free text,
   or a reference into the Financial & Economic Knowledge Layer (Phase 1A
   Stage 4 / `ECONOMIC_ONTOLOGY.md`)? Not decided here.
4. ~~Who validates that `provenance_chain` references are non-circular
   and actually resolvable...~~ **RESOLVED:** `VERIFICATION_FRAMEWORK.md`
   Section 7 assigns this to `verification-engine`, consistent with its
   auditability role (that document's Section 5.6).
5. Who issues/controls `subject` identifiers for the purpose of deciding
   which packets count as "the same question" for disagreement grouping?
   Likely ties to Stage 4, but not confirmed here.
6. **Resolved (added in this patch, Section 4a):** the corroboration
   mechanism for `PROVISIONAL` → `VERIFIED` was raised in Phase 1A v2 but
   dropped from this document's original open-questions list. It is now
   defined in Section 4a. Flagged here so the gap in tracking is visible,
   not just silently closed.
