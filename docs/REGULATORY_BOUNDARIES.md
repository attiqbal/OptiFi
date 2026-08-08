# REGULATORY_BOUNDARIES

**Status:** DRAFT (v1.1 — Phase 3, patch: Section 6 item 4 updated). This document is an architectural mapping
for internal engineering and product purposes only. **It is not a legal
opinion.** Every conclusion below requires confirmation from qualified UK
legal, tax, and regulatory professionals before being relied upon.

## 1. Purpose & Scope

This document maps the regulatory regimes relevant to OptiFi's design so
that engineering and product decisions are made with the right constraints
in view. It does not select a final regulatory posture — that decision sits
with qualified professionals and, ultimately, the business.

## 2. Relationship to Prior Documents

This document is downstream of `PRODUCT_VISION.md` (Phase 2A and its patch
adding Tax & Estate Intelligence) and `ENGINE_PIPELINE_SPECIFICATION.md`
(Phase 1A), which already established the advice-vs-guidance question as
open. This document widens that question rather than resolving it, because
Tax & Estate Intelligence introduces two further regimes beyond FCA
investment regulation.

## 3. Regulatory Domains in Scope

OptiFi's design touches at least four distinct regulatory domains. They do
not share a single answer — a feature can be fine under one and problematic
under another.

### 3.1 FCA — Investment Advice vs. Guidance

Carried forward, unresolved, from Phase 1A/2A: telling a user to take a
specific investment action (buy this, switch that, repay this debt instead
of holding this ETF) risks crossing from guidance into regulated advice
under FCA rules (COBS, Consumer Duty). Three paths remain open: full FCA
authorisation; a guidance-only product design; or a B2B2C model where a
regulated partner holds the relevant permissions. Not decided here.

### 3.2 HMRC — Tax Advice, Disclosure, and the Promoter/Enabler Regime

This is a separate regime from FCA regulation and is being actively
tightened. Relevant elements, current as of Phase 3 drafting:

- Draft Finance Bill 2026 legislation introduces a requirement for tax
  advisers who interact with HMRC on a client's behalf to register with
  HMRC and meet minimum standards, from 1 April 2026.
- The Disclosure of Tax Avoidance Schemes (DOTAS) and equivalent indirect-tax
  regime (DASVOIT) require promoters of tax avoidance arrangements to
  disclose them to HMRC. The same draft legislation makes a promoter's
  failure to notify a criminal offence and introduces "universal stop
  notices" that can prohibit promoting specified avoidance arrangements
  outright.
- **Important distinction to preserve architecturally:** ordinary use of
  reliefs and allowances Parliament intended (ISA/pension contributions,
  standard CGT allowances) is not a "tax avoidance scheme" in the DOTAS
  sense, which targets contrived or artificial arrangements. Tier 1 (Section
  4.1) should not be conflated with tax avoidance promotion. Tier 3's design
  exists precisely because *structuring* advice is where that line becomes
  genuinely uncertain.
- This is an evolving area (draft legislation as of this document's
  drafting) and must be re-checked against the enacted Finance Act before
  any Tier 2/3 feature ships.

### 3.3 Trust & Estate Law — Reserved Legal Activity

A trust requires a properly drafted trust deed — a legal instrument.
Professional legal advice (solicitors, STEP-qualified trust practitioners)
is treated as essential across professional sources on setting up a trust,
alongside separate specialist tax advice on its treatment. Trust creation
can also trigger immediate inheritance tax charges depending on structure
and value, meaning even general descriptions can shade into
circumstance-specific advice if too tailored. Whether drafting or
recommending a specific trust structure falls within a formally "reserved
legal activity" under the Legal Services Act 2007 is a technical legal
question not resolved here — the safer architectural position (Tier 3,
Section 4.3) is to avoid originating structures regardless of the precise
boundary.

### 3.4 Data Protection & Consent

The Financial Twin (`PRODUCT_VISION.md`, Section 7) aggregates highly
sensitive personal financial data. UK GDPR and the Data Protection Act 2018
apply. This domain is flagged, not detailed, here — it needs its own
dedicated treatment, likely extending `SECURITY.md` (Phase 0 placeholder) or
a future dedicated privacy document. Not performed in this task.

## 4. Applying the Tax & Estate Intelligence Tiers

Cross-referencing `PRODUCT_VISION.md`'s three tiers against the domains
above:

### 4.1 Tier 1 — Tax-Aware Optimisation
Arithmetic on published thresholds and allowances; not a tax avoidance
arrangement (Section 3.2); stays within whatever posture is eventually
adopted for FCA guidance (Section 3.1), since it's inseparable from ordinary
portfolio construction. Lowest incremental regulatory novelty of the three.

### 4.2 Tier 2 — General Tax/Estate Education
Lower risk if genuinely generic and not tailored to the user's specific
circumstances — but the line between "general education" and "advice
tailored to your circumstances" is assessed by substance, not by how the
feature is labelled in the UI. This determination needs legal review before
launch, not just an architectural intention to stay general.

### 4.3 Tier 3 — Personalised Trust/Charity Structuring (Flag-Only)
Designed specifically to stay outside Section 3.2's promoter/enabler
exposure and Section 3.3's reserved-activity question, by never having
OptiFi originate a specific structure — only flagging that professional
engagement could be valuable, then handing off to a solicitor/STEP
practitioner and a registered tax adviser. **This design intent does not, by
itself, guarantee the feature sits outside regulated territory** — that
requires confirmation from qualified counsel (Section 6, item 1).

## 5. Cross-Domain Interactions

A single feature can touch more than one domain at once. Two examples worth
flagging rather than resolving:

- A Tier 3 flag, however general, still personalises based on the specific
  user's Financial Twin — its safety depends on exact wording and degree of
  personalisation, which is a legal judgement, not an engineering one.
- A recommendation touching both investment allocation (Section 3.1) and
  tax-wrapper choice (Section 3.2/4.1) simultaneously may need clearance
  under both regimes at once, not just the more familiar FCA one.

## 6. Known Gaps / Open Questions

1. Formal confirmation from qualified UK legal/compliance counsel that the
   Tier 3 "flag, don't structure" design (Section 4.3) does not itself
   constitute regulated advice or promoter/enabler activity. Not resolved
   here — this document cannot resolve it.
2. Whether OptiFi requires HMRC tax-adviser registration once the April 2026
   regime is in force — likely not for Tier 1/2 (OptiFi doesn't contact
   HMRC on a user's behalf), but not confirmed.
3. The FCA advice-vs-guidance question (Section 3.1), inherited unresolved
   from Phase 1A/2A.
4. Data protection treatment of the Financial Twin (Section 3.4) —
   **`SECURITY.md` now provides this treatment** (its Section 1
   explicitly addresses this gap). Not a complete resolution —
   `SECURITY.md` Section 11, item 5 still asks whether a further
   dedicated `PRIVACY.md` should eventually split off from it — but this
   item should no longer read as if nothing exists yet.
5. Whether referral relationships with solicitors/STEP practitioners/tax
   advisers for the Tier 3 handoff themselves create regulatory obligations
   (e.g. financial promotion rules around introducing or referring to
   regulated advisers). Not addressed here.
6. This document's HMRC-regime description (Section 3.2) is based on draft
   legislation current at time of writing and must be re-verified against
   whatever is actually enacted before Tier 2/3 features ship.
