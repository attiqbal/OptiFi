# SECURITY

**Status:** DRAFT (v1.2 — Phase 10, patch: Section 11 item 2 fully confirmed for all three engines)

## 1. Purpose & Scope

This document specifies security requirements and a threat model specific
to OptiFi's actual architecture — not generic security boilerplate. It
elaborates the data-protection gap flagged twice already and left
unaddressed: `REGULATORY_BOUNDARIES.md` Section 3.4 and
`DATA_ARCHITECTURE.md` Section 8, item 5.

## 2. Relationship to Prior Documents

The Financial Twin (`DATA_ARCHITECTURE.md`) is the asset this document
exists to protect. The Universal Analytical Packet's `provenance_chain`,
`evidence`, `source`, and `timestamp` fields (`ANALYTICAL_CONTRACT_SPEC.md`,
Section 5) already provide a foundation for analytical audit trail — see
Section 8 below for how that differs from access audit logging. The
corroboration requirement (`ANALYTICAL_CONTRACT_SPEC.md`, Section 4a) is
reframed here as a security control, not only a data-quality one — see
Section 6.

## 3. Threat Model — What's Actually At Risk

Specific to this architecture, not generic:

- **The Financial Twin is the single highest-value target.** A breach
  exposes a complete picture of assets, liabilities, income, and — per Tax
  & Estate Intelligence — potentially IHT-relevant estate information.
  Combined with a future Tier 3 flag (currently gated, `MVP_ROADMAP.md`
  Gate B), exposure could reveal who is a high-net-worth target for
  real-world fraud or social engineering, independent of the underlying
  financial data itself.
- **The Mandate (`DATA_ARCHITECTURE.md` Section 4.1) is sensitive in its
  own right** — exact risk tolerance, minimum cash reserve, and leverage
  policy reveal financial sophistication and vulnerability, separate from
  the raw asset figures.
- **Adversarial or manipulated unstructured content is an injection-
  adjacent risk.** Stage 3's LLM-assisted extraction from news or filings
  could be manipulated into producing a false `PROVISIONAL` claim. The
  corroboration requirement is the existing defence against this — see
  Section 6.
- **Cross-user data leakage** via shared infrastructure (caching, logging,
  or the shared `ECONOMIC_ONTOLOGY.md`) is a distinct risk from external
  breach — see Section 7.
- **Execution risk does not yet exist.** `MVP_ROADMAP.md` Gate C means
  there is no capability to move money in this MVP — the threat model
  changes substantially once, if ever, that gate opens, and this document
  will need revisiting at that point, not before.

## 4. Identity & Authentication

Strong identity verification proportional to the sensitivity of Financial
Twin data. Multi-factor authentication is a baseline expectation, not an
optional enhancement, given what a compromised account exposes (Section 3).
Session management must assume the data behind it is worth targeting.

## 5. Authorisation — Following the Engine Ownership Model

Authorisation boundaries should follow a distinction already implicit in
the pipeline architecture: most of `causal-engine`, `forecast-engine`, and
`simulation-engine`'s work operates on the shared, non-personal
`ECONOMIC_ONTOLOGY.md` and produces general `ESTIMATE` output (e.g. "UK
recession probability") — these do not need raw access to any individual
user's Financial Twin. Only `quant-engine` and `optimisation-engine` need
scoped, per-user access to a specific Twin to do Stage 8/9 work. Principle
of least privilege follows this shape directly: an engine that only needs
general market/economic knowledge should never be granted per-user data
access by default.

## 6. Corroboration as a Security Control, Not Just a Quality Control

`ANALYTICAL_CONTRACT_SPEC.md` Section 4a's corroboration requirement — a
`PROVISIONAL` fact needs independent corroboration before becoming
`VERIFIED` — was designed for analytical rigour. It is also, functionally,
a defence against adversarial content: a single manipulated or fabricated
source cannot alone push a false claim to `VERIFIED` status. This should be
treated as a security requirement as much as a data-quality one going
forward, not maintained as a coincidental side benefit.

## 7. Isolation

Per-user Financial Twin data must be strictly isolated between users. The
shared `ECONOMIC_ONTOLOGY.md` (global, non-personal) is legitimately shared
infrastructure; Twin instances are not, and must not leak across users even
accidentally via shared caching, logging, or cross-referencing against
Ontology entities.

## 8. Audit Logging — Two Distinct Trails

`ANALYTICAL_CONTRACT_SPEC.md`'s UAP fields already provide an **analytical
provenance trail** — what was concluded, from what evidence, by which
engine. This document requires a second, distinct **access audit trail** —
who or what accessed a specific user's Twin data, when, and why — which the
UAP does not capture and which is not addressed anywhere else in this
project. These are not the same thing and should not be conflated into one
log.

## 9. Threat-Specific Mitigations Summary

- Adversarial/manipulated unstructured content → corroboration requirement
  (Section 6).
- Cross-user data leakage → isolation (Section 7).
- Social-engineering targeting via a future Tier 3 flag → the flag itself,
  once Gate B opens, requires the same protection level as the underlying
  financial data — being "just a flag" does not make it lower-sensitivity
  metadata.

## 10. Incident Response

UK GDPR requires notifying the ICO within 72 hours of becoming aware of a
personal data breach likely to risk individuals' rights and freedoms. This
document requires that a detection-containment-disclosure process exist
and meet that obligation — the process's operational details (on-call
ownership, notification templates) are not designed here.

## 11. Known Gaps / Open Questions

1. Exact identity/authentication mechanism and encryption/key-management
   approach are not chosen here — implementation decisions for later.
2. ~~Section 5's assumption...~~ **FULLY CONFIRMED:**
   `CAUSAL_ENGINE_SPEC.md` Section 4, `FORECAST_ENGINE_SPEC.md`
   Section 3, and `SIMULATION_ENGINE_SPEC.md` Section 4 each confirm this
   for their respective engine. None of the three need raw per-user Twin
   access — only `quant-engine` and `optimisation-engine` do.
3. Incident response process details (Section 10) are not designed here.
4. Whether a future Tier 3 flag (Section 9) requires elevated protection
   beyond ordinary Twin data, or merely equal protection, is not decided.
5. Whether this document remains the permanent home for data-protection
   requirements, or whether a dedicated `PRIVACY.md` should eventually
   split off from it (raised as a possibility in `REGULATORY_BOUNDARIES.md`
   Section 3.4), is not resolved.
