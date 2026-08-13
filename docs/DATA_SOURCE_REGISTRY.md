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

## 7. Candidate Vendor Evaluation (Phase E2) — Evaluation Only, Nothing Selected

Phase E2 built the provider-abstraction architecture (`data-engine`'s
`ProviderAdapter` interface — see that package) real vendors would plug
into, and evaluated real, named, publicly-known candidates per category
against this document's own Section 1 promise that vendor selection
"is a procurement and licensing decision for later." **No vendor below
has been selected, contracted with, or connected — every adapter
implementation status is `NOT CONNECTED`.** This section records the
evaluation so that decision, when made, starts from documented ground
rather than a blank page. Publicly-known characteristics as understood
at evaluation time; all of cost, rate limits, and terms of service
change over time and must be re-verified before any commitment, not
taken on faith from this table.

**Evaluation criteria applied** (per the Phase E2 brief): authenticity,
provenance, timestamp quality, revision/vintage support, historical
availability, update frequency, licensing/usage restrictions, API
stability, cost, rate limits, data coverage. "Authoritative/original"
preferred for macro and regulatory data specifically, per this
document's own existing guidance above.

### 7.1 Category A — Market & Pricing Data

No free, official source exists for real-time or delayed LSE-level
equity/ETF pricing — unlike macro/regulatory data (Section 7.2/7.3),
authoritative market data is inherently a paid, licensed relationship at
the exchange or vendor level. This category's decision is a genuine
cost/coverage trade-off, not a "pick the free official one" default.

| Candidate | Authoritative/Original | Latency | Revision Support | Auth | Rate Limits | Historical Depth | Licence/Use Notes | Adapter Status |
|---|---|---|---|---|---|---|---|---|
| Direct exchange feed (e.g. LSE Group data services) | Yes — original | Real-time available (paid tiers) | N/A (live ticks, not revised) | Enterprise contract | Contractual | Contractual | Redistribution typically restricted/licensed separately from internal use | NOT CONNECTED |
| Polygon.io | No — redistributor | Real-time (paid) / delayed (free) | N/A | API key | Free tier heavily limited | Multi-year on paid tiers | Commercial redistribution requires a paid plan | NOT CONNECTED |
| Alpha Vantage | No — redistributor | Delayed / EOD on free tier | N/A | API key | ~5 req/min, 25/day free tier | Multi-year | Free tier explicitly non-commercial in its ToS — re-verify before any use | NOT CONNECTED |
| Twelve Data | No — redistributor | Delayed (free) / real-time (paid) | N/A | API key | Free tier limited | Varies by plan | Re-verify commercial-use terms before adoption | NOT CONNECTED |
| Unofficial scraping (e.g. yfinance-style libraries against Yahoo Finance) | No | Delayed | N/A | None | Undocumented/unstable | Multi-year | **Explicitly against Yahoo's own ToS for this kind of use — named here only as a "do not do this" example**, not a real candidate | NOT CONNECTED — excluded on licensing grounds, not re-evaluated |

### 7.2 Category B — Macroeconomic Data

Unlike Category A, genuinely free, official, authoritative sources exist
here — matching this document's own existing preference for
authoritative/original sources for macro data (Section "Purpose &
Scope" framing above), and DATA_SOURCE_REGISTRY.md Section 5's UK-first
MVP scope.

| Candidate | Authoritative/Original | Latency | Revision Support | Auth | Rate Limits | Historical Depth | Licence/Use Notes | Adapter Status |
|---|---|---|---|---|---|---|---|---|
| ONS API (UK Office for National Statistics) | Yes — original issuer | Periodic release (matches official release calendar) | Yes — ONS publishes revisions on its own schedule | Free, no key required for most series | Reasonable for a statistics office API | Long (decades for major series) | Open Government Licence — permissive | NOT CONNECTED |
| Bank of England Interactive Database (IADB) | Yes — original issuer | Periodic release | Yes | Free | Reasonable | Long | Open, BoE's own terms | NOT CONNECTED |
| FRED (Federal Reserve Bank of St. Louis) | Yes, for US series — original issuer for some, aggregator/re-publisher for others (e.g. it also carries UK/international series sourced elsewhere) | Periodic release | Yes — and its companion ALFRED service is specifically built for vintage/revision history, the closest real-world match to this project's own `supersede()` mechanism | Free API key | Generous, documented | Very long | Public domain / open, St. Louis Fed's own terms | NOT CONNECTED |
| Eurostat API | Yes, for EU series — original issuer | Periodic release | Yes | Free | Reasonable | Long | Open | NOT CONNECTED — lower priority given UK-first MVP scope |

### 7.3 Category C — Company Fundamentals & Filings

| Candidate | Authoritative/Original | Latency | Revision Support | Auth | Rate Limits | Historical Depth | Licence/Use Notes | Adapter Status |
|---|---|---|---|---|---|---|---|---|
| Companies House API (UK) | Yes — original issuer/registrar | Periodic (filing-driven) | Filings are versioned/amendable documents, not silently overwritten | Free API key | Reasonable | Full filing history per company | Open, Companies House's own terms | NOT CONNECTED |
| RNS (Regulatory News Service, via LSE) | Yes — the authoritative UK regulatory-announcement channel for listed companies (earnings, guidance, corporate actions) | Real-time announcement feed (paid access tiers exist; some free delayed access) | N/A — each announcement is its own discrete, dated release | Contractual for full/real-time access | Contractual | Long | Access/redistribution terms vary by tier — re-verify | NOT CONNECTED |
| Third-party fundamentals aggregators (e.g. Financial Modeling Prep, Alpha Vantage fundamentals) | No — redistributor | Delayed | Depends on provider — not guaranteed | API key | Tiered | Varies | Re-verify commercial terms | NOT CONNECTED |

### 7.4 Category D/E — Events, News, Central-Bank & Regulatory

| Candidate | Authoritative/Original | Latency | Auth | Rate Limits | Licence/Use Notes | Adapter Status |
|---|---|---|---|---|---|---|
| Bank of England press releases / MPC decisions (direct) | Yes — original issuer, for central-bank policy decisions specifically | Real-time at publication | Free, no key | N/A (direct publication feed) | Open | NOT CONNECTED |
| FCA news/publications (direct) | Yes — original issuer, for regulatory announcements | Real-time at publication | Free | N/A | Open | NOT CONNECTED |
| RNS (see 7.3) | Yes, for company earnings/guidance-change announcements specifically | Real-time (paid) | Contractual | Contractual | Re-verify | NOT CONNECTED |
| GDELT Project | No — aggregator, broad and largely unfiltered | Near-real-time | Free | Generous | Open, but coverage far exceeds this phase's "limited, high-quality event categories" scope — explicitly a poor fit for the MVP's own scope discipline, not evaluated further | NOT CONNECTED — out of scope by design |
| General news aggregator APIs (e.g. NewsAPI.org) | No — redistributor | Delayed on free tiers | API key | Tiered | Free-tier commercial redistribution typically restricted — re-verify | NOT CONNECTED |

### 7.5 What This Evaluation Does Not Decide

Per Section 6 item 1 (unchanged, still governing): **actual selection,
contracting, cost approval, and API-key provisioning remain a
procurement decision, not made in this document or by this evaluation.**
The clearest emerging shape, stated as an observation rather than a
decision: Category B (macro) and part of Category D/E (central-bank/
regulatory) have genuinely free, authoritative, official candidates
requiring no real cost/licensing negotiation (ONS, Bank of England,
FCA), while Category A (market pricing) and the higher-fidelity parts of
Category C/D (RNS, real-time market data) do not — those categories'
adapters cannot be connected without an actual paid vendor relationship
being approved first.
