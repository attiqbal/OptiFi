# DATA_SOURCE_REGISTRY

**Status:** DRAFT (v1 — Phase 1C-1)

## 1. Purpose & Scope

This document defines the categories of external data OptiFi's `data-engine`
ingests (Phase 1A, Stage 1), and the boundary between MVP scope and future
ambition. It names no specific vendors, feeds, or providers — that is a
procurement and licensing decision for later, informed by this category
structure.

## 2. Relationship to Prior Documents

This document elaborates Phase 1A capabilities 1–5 (owned by `data-engine`)
and the "Market Intelligence" concept referenced but deliberately left
uncategorised in `PRODUCT_VISION.md` (Phase 2A) pending this document.
Section 5 below is new: it did not exist in any prior phase and responds
directly to a scope expansion requested after Phase 3.

## 3. Category Taxonomy

**A. Market & Pricing Data** — equities, ETFs, bonds, FX, commodities;
real-time or near-real-time pricing for held and researchable instruments.

**B. Macroeconomic Data** — official statistical releases: rates, inflation,
GDP, employment, yield curves, liquidity measures, currency data.

**C. Company Fundamentals & Filings** — earnings, financial statements,
regulatory filings, corporate actions, guidance, management changes.

**D. Financial News** — market, company, and sector news. This is the
primary feed into Stage 3's unstructured-text extraction pathway
(`ENGINE_PIPELINE_SPECIFICATION.md`, Section 9) and therefore the primary
source of `PROVISIONAL`-status facts.

**E. Regulatory & Policy Sources** — new in this document. See Section 4.

**F. Alternative / Supplementary Data** — sentiment, alternative datasets,
etc. Explicitly future, not MVP.

## 4. Regulatory & Policy Sources — Two Distinct Consumers

Regulatory and policy information (FCA rule changes, Bank of England policy,
HMRC guidance and allowance changes, and relevant international regulation)
feeds **two different, architecturally separate consumers**. Conflating them
is a design error to avoid:

**4.1 User-Facing Consumer.** Regulatory/policy changes relevant to a user's
own financial position flow through the standard pipeline (Stages 1–4) like
any other data, eventually surfacing as `JUDGEMENT`-class output (e.g. "the
ISA allowance changed, here's what that means for you"). This is a normal
extension of Category D/E ingestion — no new pipeline stage is needed.

**4.2 Product-Compliance Consumer.** The same category of source also needs
to inform OptiFi's *own* compliance posture — specifically, the open item in
`REGULATORY_BOUNDARIES.md` (Section 6, item 6) that its HMRC-regime
description is based on draft legislation and must be re-verified once
enacted. This is an internal, non-user-facing process, not a pipeline stage,
and its ownership is not decided here — see Section 6.

## 5. Tiered Scope — MVP vs. Future

"Comprehensive coverage" is the long-term ambition. It is not the MVP scope,
which remains governed by `PRODUCT_VISION.md` Section 14.

**MVP (V0.1):**
- Category A: pricing for the user's actual held instruments only (per the
  20–30 equity/ETF MVP scope), not the full market.
- Category B: a small, defined set of official UK macro releases (the
  releases that already exist as named indicators in the MVP definition).
- Category C: filings for held companies only.
- Category D: a small, defined set of reputable UK/international financial
  news sources — not "all sources."
- Category E: FCA, Bank of England, and HMRC policy announcements relevant
  to retail/SME finance in the UK — not global regulatory coverage.
- Category F: excluded from MVP entirely.

**Future:** broaden geographic coverage beyond the UK, widen news source
breadth, add alternative data (Category F), and extend regulatory monitoring
to other jurisdictions as the product's user base requires it. None of this
is scheduled here — it is scope for `MVP_ROADMAP.md` to sequence later.

## 6. Known Gaps / Open Questions

1. Actual vendor and licensing decisions — cost, coverage, legal terms — are
   deliberately out of scope for this document and remain a procurement
   decision.
2. Ingesting "all news available online" raises its own legal/ToS questions
   independent of cost — many news sources' terms of use restrict automated
   scraping regardless of technical feasibility. Not resolved here.
3. Ownership of the Product-Compliance Consumer (Section 4.2) — is this a
   `verification-engine` responsibility, a standalone internal process, or
   something else? Not decided here.
4. How Category E sources are validated for corroboration before being
   treated as trustworthy is addressed in the companion patch to
   `ANALYTICAL_CONTRACT_SPEC.md` (Phase 1C-2), not in this document.
