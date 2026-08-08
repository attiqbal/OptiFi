# MVP_ROADMAP

**Status:** DRAFT (v1 — Phase 4)

## 1. Purpose & Scope

This document sequences what OptiFi builds, and formally gates features
whose prerequisites are not yet met. A gate here is a hard stop: a feature
must not be built — in full or in a reduced form — until its listed
condition is met and this document is updated to reflect that. Softening a
gated feature's language or scope does not remove its gate; see Section 5.

## 2. Relationship to Prior Documents

MVP scope is drawn from `PRODUCT_VISION.md` Section 14. Gate conditions are
drawn from `REGULATORY_BOUNDARIES.md` Section 6 and `PRODUCT_VISION.md`
Section 18. This document does not introduce new open questions of its own —
it organises existing ones as enforceable build gates.

## 3. V0.1 — Buildable Now, No Gate

- The MVP scope defined in `PRODUCT_VISION.md` Section 14: one user, one
  manually entered portfolio, 20–30 equities/ETFs, a basic risk profile,
  live/near-live prices, a small set of macro indicators, a small set of
  financial news sources, portfolio analytics, basic causal intelligence, a
  small number of forecasts, scenario simulation, CIO synthesis.
- **Tier 1 — Tax-aware optimisation** (`PRODUCT_VISION.md` Section 6):
  computational, sits inside the existing `optimisation-engine` constraint
  set. No gate.

## 4. Gated Features

### Gate A — Tier 2: General Tax/Estate Education
**Condition:** a compliance content review confirming the material stays
genuinely generic and is never tailored to a specific user's circumstances
(`REGULATORY_BOUNDARIES.md`, Section 4.2). Lighter-weight than Gate B, but
still a real review, not a design assumption.
**Status:** OPEN.

### Gate B — Tier 3: Personalised Trust/Charity Structuring (Flag-Only)
**Condition:** formal confirmation from qualified UK legal/compliance
counsel that the flag-only design (`PRODUCT_VISION.md` Section 6) does not
itself constitute regulated advice or promoter/enabler activity
(`REGULATORY_BOUNDARIES.md`, Section 6, item 1).
**Status:** DESIGNED, GATED. The design is complete and intentionally
preserved as-is — it is not being removed or watered down. It is not to be
built, in this or any reduced form, until the condition above is met.

### Gate C — Execution Roadmap Stages 2–5 (Recommend / Prepare / Approve / Execute)
**Condition:** resolution of the FCA advice-vs-guidance classification
(`REGULATORY_BOUNDARIES.md`, Section 3.1 and Section 6, item 3).
**Status:** OPEN.

### Gate D — Stage 5 Specifically (Agent Execution Within Mandate)
**Condition:** formal definition of the "KYA framework" referenced in
`PRODUCT_VISION.md` Section 13, which does not exist in any OptiFi document
today (`PRODUCT_VISION.md`, Section 18, item 1).
**Status:** OPEN, undefined.

## 5. Gate Enforcement Principle

A gate blocks the feature it names, not just its current wording. If a
smaller, softer, or differently-worded version of a gated feature is
proposed as a way to ship sooner, that proposal must be evaluated against
the same gate condition — it is not assumed safe merely because it is
narrower in scope. This applies with particular force to Gate B: rephrasing
a personalised flag in more hedged or probabilistic language does not change
whether it functions as advice in substance, and does not clear the gate.

## 6. Business / Operational Gates (Distinct from Feature Gates)

These affect OptiFi as a business, not a specific product feature, and are
listed for completeness rather than sequenced here:

- Whether OptiFi requires HMRC tax-adviser registration once the April 2026
  regime is in force (`REGULATORY_BOUNDARIES.md`, Section 6, item 2).
- Whether referral relationships with solicitors/STEP practitioners/tax
  advisers for the Gate B handoff themselves create regulatory obligations
  (`REGULATORY_BOUNDARIES.md`, Section 6, item 5).
