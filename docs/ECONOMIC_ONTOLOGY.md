# ECONOMIC_ONTOLOGY

**Status:** DRAFT (v1.1 — Phase 5-2, patch: Section 7 item 3 resolved — subject proposal not adopted)

## 1. Purpose & Scope

This document defines the shared entities, classifications, and
relationships that the Financial Twin (`DATA_ARCHITECTURE.md`) references
and that `causal-engine` reasons over — global knowledge, not per-user data.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 4 (Financial & Economic
Knowledge Layer, jointly owned by `data-engine` and `causal-engine`).
`DATA_ARCHITECTURE.md` Section 5 already assumes holdings reference entities
defined here rather than duplicating them.

## 3. Entity Categories

**Financial Instruments** — types/classes (equity, bond, fund, ETF, deposit,
property), not a registry of every actual instrument.

**Issuing Entities** — companies, governments, funds — the things that
issue or stand behind instruments.

**Classification Systems** — sector, industry, country, currency. These
reference the *category* of an external classification standard, not a
specific named one — which standard to adopt is a later, more operational
decision.

**Economic Concepts** — macro indicators as defined concepts (GDP,
inflation, interest rates) — what the concept *is*, not its current value.
Live values are `FACT`/`ESTIMATE` output flowing through the pipeline
(`ENGINE_PIPELINE_SPECIFICATION.md` Stages 1–6), not stored here.

**Relationships** — ownership, subsidiary structure, sector membership,
and causal links. Causal relationships specifically are `causal-engine`'s
Stage 5 output — see Section 6.

## 4. Entity Identifiers

Every entity in this ontology has a stable identifier, used for
`cause_entity_id`, `effect_entity_id`, and `affected_entity_id` fields
in `causal-engine` and `simulation-engine`. The earlier proposal that
these identifiers also anchor `subject` values
(`DATA_ARCHITECTURE.md` Section 6) was considered and **not adopted** —
`subject` uses free natural-language text across all implemented
engines. See `DATA_ARCHITECTURE.md` Section 6 for the full resolution.

## 5. Governance

Who is authorised to mint a new entity in this ontology — and therefore a
new possible `subject` root — is not decided here. This matters beyond
convenience: an ungoverned ontology means two engines could each mint
slightly different identifiers for the same real-world entity, silently
breaking the disagreement-grouping mechanism Phase 1A Section 7 depends on.
Flagged as a priority open question, not resolved.

## 6. Relationship to Causal Engine

`causal-engine`'s Stage 5 output (`ENGINE_PIPELINE_SPECIFICATION.md`) should
express causal relationships between entities *defined here*, referenced by
their identifiers — not as free text describing the relationship. This
keeps causal claims structured and traceable, consistent with the
"grounded at every stage" principle (Phase 1A, Section 4).

## 7. Known Gaps / Open Questions

1. Governance for minting new entities (Section 5) is unresolved — this is
   the same open item `DATA_ARCHITECTURE.md` Section 8 points to here; it
   is not resolved in either document.
2. Which specific external classification standards to adopt (Section 3)
   is an operational decision, not made here.
3. ~~Whether the `subject` proposal...~~ **RESOLVED:** not adopted —
   `subject` uses free natural-language text; see
   `DATA_ARCHITECTURE.md` Section 6.
4. How entity identifiers are versioned when an entity's classification
   changes (e.g. a company changes sector) is not addressed.
5. Whether this ontology needs its own audit/verification process, similar
   in spirit to `verification-engine`'s role elsewhere in the pipeline, is
   not decided.
