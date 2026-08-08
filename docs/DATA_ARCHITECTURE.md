# DATA_ARCHITECTURE

**Status:** DRAFT (v1.1 — Phase 5-1, patch: Capital Efficiency ownership follow-up)

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
objective.

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

## 6. Proposal: Resolving the `subject` Identifier Question

`ANALYTICAL_CONTRACT_SPEC.md` (Section 9, items 3 and 5) left open what
governs `subject` identifiers and who issues them. Proposal: a `subject`
identifier is composed of an `ECONOMIC_ONTOLOGY.md` entity identifier plus a
question-type qualifier — for example, an entity identifier for "UK economy"
combined with a qualifier like "recession probability, 12-month horizon."
This gives competing model outputs a structured, non-arbitrary basis for
grouping, rather than free text that different engines might phrase
differently for the same underlying question. **This is a proposed
mechanism, not a governance answer** — who is authorised to mint new
Ontology entities (and therefore new possible `subject` roots) is addressed
in `ECONOMIC_ONTOLOGY.md` Section 5, and remains open there.

## 7. Mandate Freshness

Section 4.1's mandate parameters can go stale — a risk tolerance stated
two years ago may no longer reflect the user's actual situation. This
document flags the need for a review/reconfirmation cadence without
specifying one; see Section 8.

## 8. Known Gaps / Open Questions

1. No review/reconfirmation cadence is defined for mandate parameters
   (Section 7) — when they should transition to `STALE` is not decided.
2. Governance for minting new `ECONOMIC_ONTOLOGY.md` entities (Section 6)
   is deferred to that document and not resolved there either — both
   documents currently point at each other on this question.
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
