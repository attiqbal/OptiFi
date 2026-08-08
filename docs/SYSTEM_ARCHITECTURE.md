# SYSTEM_ARCHITECTURE

**Status:** DRAFT (v1 — Phase 14)

## 1. Purpose & Scope

This document specifies OptiFi's service boundaries and how they
communicate — the technical architecture underneath the analytical pipeline
already fully specified elsewhere. It does not choose implementation
technology.

## 2. Relationship to Prior Documents

Directly answers `ENGINE_PIPELINE_SPECIFICATION.md` Section 11, which
named `backend`'s technical orchestration as this document's concern and
left it unwritten. Formalises `ANALYTICAL_CONTRACT_SPEC.md`'s Universal
Analytical Packet as the interchange format between every service boundary
described here.

## 3. Service Boundaries

Matching the repository structure already created in Phase 0:

- **The eight engines** (`data-engine`, `causal-engine`, `quant-engine`,
  `forecast-engine`, `simulation-engine`, `optimisation-engine`,
  `ai-engine`, `verification-engine`) — each a distinct service boundary,
  each fully specified in its own document.
- **`backend`** — owns technical orchestration (Section 5).
- **`frontend`** — consumes `backend`'s finalised output and renders
  `APP_UX_BLUEPRINT.md`'s screens; contains no analytical logic of its own.
- **`shared`** — cross-engine utilities and the common UAP representation
  every engine uses (Section 4).
- **`infrastructure`** — deployment, configuration, observability; not
  detailed in this document.

## 4. The UAP as the Universal Interchange Format

Every service boundary in Section 3 communicates using the Universal
Analytical Packet (`ANALYTICAL_CONTRACT_SPEC.md`, Section 5) — engines do
not need bespoke point-to-point protocols between each pair; they all speak
one common contract. This is what makes the eight-engine architecture
tractable as a system, not just as a diagram.

## 5. Backend's Technical Orchestration Responsibilities

Answering `ENGINE_PIPELINE_SPECIFICATION.md` Section 11's open pointer,
`backend`:

- **Sequences pipeline execution** per the 14 stages
  (`ENGINE_PIPELINE_SPECIFICATION.md`, Section 9), routing each stage's UAP
  output to the correct next engine(s).
- **Tracks `disagreement_set_ref` groupings** (`ANALYTICAL_CONTRACT_SPEC.md`,
  Section 7) — knowing when a plural set of competing model outputs sharing
  one `subject` is complete enough for Stage 12 to proceed, rather than
  treating pipeline stages as strictly linear and single-threaded.
- **Enforces `MVP_ROADMAP.md`'s gates at the routing level**, as
  defense-in-depth alongside `optimisation-engine`'s own Stage 9b check
  (`OPTIMISATION_ENGINE_SPEC.md`, Section 8) — a third layer, not a
  replacement for the other two.
- **Does not make analytical judgements.** This is *technical*
  orchestration; `ai-engine`'s Stage 12 *analytical* orchestration remains
  entirely separate (`ENGINE_PIPELINE_SPECIFICATION.md`, Section 11) —
  restated here, not redefined.

## 6. Frontend's Role

Consumes `backend`'s Stage 13 output and renders it per
`APP_UX_BLUEPRINT.md`. Contains no analytical logic — `information_class`
and `validation_status` distinctions arrive already resolved from the
pipeline; `frontend` displays them, it does not compute or interpret them.

## 7. Deployment Architecture

Deliberately unspecified — cloud platform, containerisation strategy, and
scaling approach are operational decisions for a later phase, not part of
this document.

## 8. Known Gaps / Open Questions

1. Communication technology between service boundaries (Section 3) is not
   chosen — implementation decision for later.
2. Whether the eight engines are deployed as separate services or as
   modules within a single deployable unit for MVP is not decided — a
   simpler monolithic MVP deployment may be reasonable even though the
   logical architecture treats them as eight distinct boundaries.
3. The exact mechanism `backend` uses to track "complete" disagreement sets
   before Stage 12 can proceed (Section 5) needs real design — not
   specified here beyond the requirement that it exists.
4. Whether `backend` eventually needs its own full specification document,
   given this document covers only its orchestration role conceptually —
   this partially closes the gap Phase 0 flagged for `backend` having no
   spec at all, but does not fully resolve it.
5. Deployment architecture (Section 7) is entirely deferred.
