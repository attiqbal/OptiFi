# DATA_ARCHITECTURE

**Status:** DRAFT (v1.3 — Phase 5-1, patch: subject field resolved as free text)

## 1. Purpose & Scope

This document defines the Financial Twin's data model — what it conceptually
contains and how it's represented — not its storage technology. Global,
shared classification and entity data (what a "sector" is, what a specific
company is) lives in `ECONOMIC_ONTOLOGY.md`; this document covers only
per-user data.

## 2. Relationship to Prior Documents

Elaborates `PRODUCT_VISION.md` Sections 7 (Financial Twin, conceptual) and 8
(User Mandate, conceptual). Every field in the Twin uses the Universal
Analytical Packet shape from `ANALYTICAL_CONTRACT_SPEC.md` — see Section 3.
Holdings reference entities defined in `ECONOMIC_ONTOLOGY.md` rather than
duplicating classification data — see Section 5.

## 3. Core Principle: The Twin Is a Collection of UAPs, Not a Separate Format

The Financial Twin is not a bespoke data structure. It is a queryable,
continuously-updated collection of Universal Analytical Packets
(`ANALYTICAL_CONTRACT_SPEC.md`, Section 5), all with `subject` values scoped
to one user. This keeps the Twin consistent with every other piece of
analytical output in the system rather than inventing a parallel
representation with its own rules. A holding's current value is a UAP; a
computed exposure percentage is a UAP; a stated risk tolerance is a UAP.

## 4. Top-Level Structure

### 4.1 Identity & Mandate
User-stated parameters, each represented as a UAP with
`information_class: FACT` (a stated preference is a fact about what the
user told the system) and `validation_status: VERIFIED` by default (direct
from the user, nothing to corroborate) — but subject to becoming `STALE` if
never reconfirmed; see Section 7.

Parameters: risk tolerance, maximum acceptable drawdown, investment
horizon, minimum cash reserve, maximum individual-position allocation,
maximum sector allocation, crypto ceiling, leverage policy, stated
objective, maximum single-period loss (a VaR-based ceiling, distinct
from maximum acceptable drawdown — see `OPTIMISATION_ENGINE_SPEC.md`
Section 5.1a for how it constrains the solver).

### 4.2 Assets
Cash, deposits, equities, funds, bonds, property, trust holdings, and
charitable-giving vehicles the user already has (per
`PRODUCT_VISION.md` Section 7's patch — representing an existing structure
is unrestricted; only originating a new one is Gate B territory), and other
asset types. Each holding is a UAP referencing:

- an entity defined in `ECONOMIC_ONTOLOGY.md` (e.g. which company, which
  instrument type)
- a quantity/value, `information_class: FACT`, sourced from the holding
  record itself
- its own provenance (source, timestamp) independent of the entity
  definition it references

### 4.3 Liabilities
Mortgage, loans, other debt — same UAP structure as Assets.

### 4.4 Derived Portfolio Characteristics
Sector, country, currency, and factor exposure, and concentration. These
are **not** raw held state — they are computed from Sections 4.2–4.3.
Consistent with `ENGINE_PIPELINE_SPECIFICATION.md` Stage 8's existing rule:
pure arithmetic aggregation (e.g. total cash across accounts) is `FACT`;
anything involving a risk or exposure model (e.g. expected volatility
contribution by sector) is `ESTIMATE`. This document does not re-derive that
rule — it applies it.

## 5. Relationship to the Economic Ontology

Every holding in Section 4.2/4.3 references an `ECONOMIC_ONTOLOGY.md`
entity rather than duplicating that entity's classification (sector,
country, currency, issuer) per user. This keeps classification data
centralised and consistent — if a company's sector classification changes,
it changes once in the Ontology, not once per user holding it.

## 6. Resolved: `subject` Uses Free Natural-Language Text

This section originally proposed that a `subject` value be composed of
an `ECONOMIC_ONTOLOGY.md` entity identifier plus a question-type
qualifier. **That proposal was not adopted.** Across all seven
implemented engines (~35 call sites in the current codebase), `subject`
values are consistently free natural-language text — e.g. "CIO synthesis
across disagreement groups," "minimum-variance portfolio: A, B, C" —
matching the style of the original example in
`ANALYTICAL_CONTRACT_SPEC.md` Section 5 itself ("US recession
probability, 12-month horizon"), which was never structured either. Free
text is the confirmed standard going forward, not an interim stopgap.

This does not fully resolve the risk the original proposal was trying to
prevent — different engines phrasing the same underlying question
differently, which would silently break the `disagreement_set_ref`
grouping mechanism (`ANALYTICAL_CONTRACT_SPEC.md` Section 7). Nothing
currently enforces consistent phrasing for the same question — see
Section 8, new item below.

Entity identifiers from `ECONOMIC_ONTOLOGY.md` remain in use elsewhere —
`cause_entity_id`/`effect_entity_id` in `causal-engine`,
`affected_entity_id` in `simulation-engine` — just not for constructing
`subject` values.

## 7. Mandate Freshness

Section 4.1's mandate parameters can go stale — a risk tolerance stated
two years ago may no longer reflect the user's actual situation. This
document flags the need for a review/reconfirmation cadence without
specifying one; see Section 8.

## 8. Known Gaps / Open Questions

1. No review/reconfirmation cadence is defined for mandate parameters
   (Section 7) — when they should transition to `STALE` is not decided.
2. Governance for minting new `ECONOMIC_ONTOLOGY.md` entities is still
   open — this no longer relates to `subject` construction (Section 6,
   resolved), but still applies to entity identifiers used elsewhere
   (`cause_entity_id`, `effect_entity_id`, `affected_entity_id`).
3. ~~Which engine computes the Section 4.4 derived characteristics...~~
   **RESOLVED:** `QUANT_ENGINE_SPEC.md` Section 4 formally assigns
   Capital Efficiency Score and Section 4.4's derived characteristics to
   `quant-engine`. `ENGINE_PIPELINE_SPECIFICATION.md` Section 10's
   ownership table is updated in this same patch batch (Part C) to
   reflect it.
4. Storage technology, query patterns, and update frequency for the Twin
   are all deliberately unaddressed here.
5. Consent and data protection treatment of the Twin's aggregated personal
   financial data remains deferred to a future document, per
   `REGULATORY_BOUNDARIES.md` Section 3.4.
6. Now that `subject` is confirmed free text, nothing enforces that two
   packets about the same underlying question use matching phrasing —
   a real risk to the `disagreement_set_ref` grouping mechanism that
   the original structured proposal would have prevented. Not resolved
   here.
