# APP_UX_BLUEPRINT

**Status:** DRAFT (v1.3 — Phase 2B, patch: Section 10 internal reference corrected)

## 1. Purpose & Scope

This document defines OptiFi's screens, navigation, and recurring UX
patterns — content and structure, not visual design (colour, type,
spacing — deferred to Phase 2C / dedicated design work). It translates
`PRODUCT_VISION.md`'s principles into what the user actually sees.

## 2. Relationship to Prior Documents

Downstream of `PRODUCT_VISION.md` (Phase 2A), and must stay consistent with:
`ANALYTICAL_CONTRACT_SPEC.md` for `FACT`/`ESTIMATE`/`JUDGEMENT` and
`validation_status`; `MVP_ROADMAP.md` for what's buildable versus gated;
`DATA_SOURCE_REGISTRY.md` for what categories of information exist to show;
`ENGINE_PIPELINE_SPECIFICATION.md` for which engine actually produced what.
Where this document illustrates the engine team as an "analyst team"
(Section 11), that illustration is descriptive only —
`ENGINE_PIPELINE_SPECIFICATION.md` Section 10 remains authoritative.

## 3. Standing UI Constraints (Apply to Every Screen)

These are not per-screen suggestions — they are enforced constraints on
anything built from this document:

- **No directive investment language.** Never "Buy X" / "Sell X" — the FCA
  advice-vs-guidance question (`REGULATORY_BOUNDARIES.md`, Section 3.1)
  remains open. Screens describe fit against the user's constraints, not
  instructions.
- **No transaction or execution controls anywhere.** Consistent with
  `MVP_ROADMAP.md` Gate C. Every call-to-action in this MVP is "Review,"
  "Compare," "Analyse," "Learn more," or "Monitor" — never "Execute," "Buy,"
  or "Confirm order."
- **Every `FACT` / `ESTIMATE` / `JUDGEMENT` must be visually distinguishable**
  from the others, and a non-`VERIFIED` `validation_status` must be visibly
  flagged wherever that item reaches the user — not silently presented as
  equally trustworthy.
- **The Capital Efficiency Score is displayed as a computed figure, not an
  opinion.** UI copy must never imply the CIO "decided" the score — it is
  produced by transparent quantitative rules (`PRODUCT_VISION.md`,
  Section 11a).
- **"No opportunity" is a valid, displayable state.** The Opportunity Feed
  must never manufacture a card to fill space.
- **Gate B (Tier 3) content is designed, not built.** It appears in this
  document as a marked mockup only — see Section 6.
- **Tax/estate content never states a specific quantified personal benefit
  tied to a named structure.** This is the exact line that separates
  acceptable generic education from the kind of personalised claim that
  reads as advice regardless of hedging language — see Section 6 for the
  worked example.

## 4. App Navigation

Seven tabs: **Today** (home) · **Portfolio** · **Opportunities** · **Risk**
· **Research** · **Scenario Lab** · **Ask OptiFi**.

## 5. Screen: Today (Home)

The primary screen. Not a dashboard — a briefing.

```text
GOOD MORNING

Portfolio Value          £428,600
Capital Efficiency        84 / 100
Risk                      6.3 / 10   (Target: 6 / 10)

────────────────────────────────
3 DEVELOPMENTS MATTER TODAY

1. UK interest-rate expectations changed
   Portfolio impact: Moderate
   Affected: UK Banks, Gilts, GBP
   Suggested action: NO ACTION

2. Semiconductor earnings revisions improved
   Your exposure: 18.4%
   Impact: Positive
   Suggested action: MONITOR

3. £24,000 idle cash detected
   Potential annual improvement: £816
   Suggested action: REVIEW OPTIONS
────────────────────────────────
```

Every "suggested action" stays within the Section 3 vocabulary
(Review/Monitor/No action) — never a directive.

## 6. Screen: Opportunity Feed

Not a transaction feed — an opportunity feed, spanning Tiers 1 and 2 freely,
with Tier 3 shown only as a marked, non-functional mockup.

**Tier 1 example (buildable now):**
```text
£920/year opportunity
Your cash reserve exceeds your selected liquidity requirement by £26,000.
Eligible alternatives currently provide higher expected yield.
[Review]
```

**General example (buildable now):**
```text
Portfolio concentration
Technology exposure has moved from 22% → 28%. Your target maximum: 25%.
[Analyse]
```

**Tier 2 note:** general tax/estate education (e.g. "how ISA allowances
work") surfaces as informational content within Research or Opportunities,
never phrased as advice tailored to the user's specific figures — gated on
`MVP_ROADMAP.md` Gate A (content review), not built by default in this
document.

**Tier 3 — GATED, mockup only, not to be wired to real logic:**
```text
[GATED — MVP_ROADMAP.md Gate B — design only, not implemented]

Estate planning may be worth exploring
Your financial profile suggests this could be an area worth professional
review.
[Learn what this means]   [Find a qualified professional]
```

**Explicit design rule, not optional:** this card must never resemble the
following, which is the exact pattern that crosses into advice regardless
of phrasing:
```text
✗ NEVER: "Your estate could save up to £140,000 with a discretionary trust."
✗ NEVER: naming a specific structure, or a specific £ figure tied to the
  user's own numbers.
```
The safe version names no structure and no personal figure — it only
signals that professional review may be worth the user's time, and routes
to education or a referral, never to a recommendation.

**No-opportunity state:**
```text
No new opportunities today. Your capital allocation remains efficient
against your current mandate.
```

## 7. Screen: Portfolio

The user's full balance sheet, not just an investment account.

```text
TOTAL CAPITAL          £428,600
Assets                  £548,600
Liabilities             £120,000
Net Capital             £428,600
```

Analytical panels: Allocation, Risk, Liquidity, Income, Currency exposure,
Sector exposure, Geographic exposure, Concentration, Expected volatility,
Drawdown scenarios. Each panel's figures carry their `information_class` —
current holdings values are `FACT`; volatility, drawdown, and exposure
projections are `ESTIMATE`.

## 8. Screen: Research (Asset / Company)

Standard sections (Price, Valuation, Fundamentals, Earnings trend, Analyst
revisions, Sector position, Competitive position, Macro sensitivity, News,
Risk), followed by the personalised section that differentiates this from a
generic stock page:

```text
[COMPANY] + You

Current portfolio exposure:     0%
If £10,000 invested:            2.3%
Sector exposure:                18.2% → 20.5%
Portfolio risk:                 6.1 → 6.3
Currency exposure:              EUR +2.3%
Target constraints:             PASS
```

**OptiFi assessment — required framing, per Section 3:**
```text
✗ NEVER: "BUY [COMPANY]."
✓ REQUIRED STYLE: "[Company] currently fits within your portfolio
  constraints, although sector exposure would increase materially. Under
  your current mandate, an allocation larger than £X would approach your
  chosen sector limit."
```
This is `JUDGEMENT`, explicitly traceable to the `FACT`/`ESTIMATE` figures
above it — never presented as a standalone conclusion.

## 9. Market Intelligence (Relevance Filtering)

OptiFi continuously observes the categories defined in
`DATA_SOURCE_REGISTRY.md` (market/macro/company/news/regulatory-policy), but
the product only ever surfaces what's relevant: the standing question is
"does this matter to this user's Financial Twin?" — if no, deprioritise; if
yes, analyse and potentially surface on Today or in the Opportunity Feed.
This is a filtering principle, not a new data category — the categories
themselves are `DATA_SOURCE_REGISTRY.md`'s, not redefined here.

## 10. Screen: Scenario Lab

User selects a scenario (MVP: from a preset list, not free-form, per
`SIMULATION_ENGINE_SPEC.md` Section 5's recommendation — see this
document's Section 17, item 5); OptiFi propagates it and evaluates the
user's actual portfolio. Consistent with the forecasting philosophy
(`PRODUCT_VISION.md`, Section 11) — plausible futures, not predictions:

```text
Estimated portfolio impact
Base simulation:     +2.8%
Range:               -1.4% to +5.7%
Most positively affected:  UK Gilts, Property holdings
Potential negative:        UK Banks
Confidence:                Moderate
Key uncertainty:           GBP response
```

## 11. The Analyst-Team Illustration (Non-Authoritative)

For onboarding/explanatory use only — informally conveys that some
"analysts" are LLMs, some are mathematical models, some are databases, and
the user doesn't need to know which is which. **If this illustration and
`ENGINE_PIPELINE_SPECIFICATION.md` Section 10 ever appear to disagree, that
document governs, not this one.**

```text
                 CIO
                  │
          Manager / OptiFi AI
                  │
     ┌────────────┼─────────────┐
     │            │             │
 Macro        Markets       Portfolio
 Analyst      Analyst        Analyst
     │            │             │
     └────────────┼─────────────┘
                  ▼
              CIO Brief
```

## 12. The "Why?" Drill-Down Pattern

Every recommendation-shaped statement has a "Why?" control. The drill-down
must show each contributing engine's output labelled with its
`information_class`, and flag any `validation_status` that isn't `VERIFIED`:

```text
Suggested: Reduce technology exposure by approximately 3%

Why?

[FACT — data-engine/quant-engine]
Technology exposure: 28.3% (target maximum: 25%)
       ↓
[ESTIMATE — quant-engine]
Technology contributes 34% of expected portfolio volatility
       ↓
[ESTIMATE — forecast-engine · validation_status: PROVISIONAL,
 pending corroboration]
Sector outlook remains positive over the forecast horizon
       ↓
[ESTIMATE — optimisation-engine]
A 3% reduction improves diversification without materially changing
expected return. Constraints: PASS
       ↓
[Verdict — verification-engine]
PASS WITH CAUTION
       ↓
[JUDGEMENT — ai-engine]
Framing and explanation above, citing each input
```

Sources are visible beneath, not hidden behind another click.

## 13. Confidence Visibility

Important conclusions show a confidence label; expanding it shows its
basis — this is not a single invented number, it's a breakdown:

```text
Confidence: Moderate

Data quality:          High
Model agreement:       Moderate
Data freshness:        Current
Causal distance:       Medium
Conflicting signals:   2
Overall confidence:    Moderate
```

## 14. Capital Efficiency Score Display

```text
82 / 100

Cash efficiency        68
Investment efficiency  87
Risk efficiency        83
Debt efficiency        91
Tax efficiency         77
Liquidity efficiency   96
```

Per Section 3: this is a computed figure from transparent rules. UI copy
must never phrase it as the CIO's judgement or opinion.

## 15. Screen: Business Mode

Same intelligence engine, different portfolio — capital and treasury only,
consistent with `PRODUCT_VISION.md` Section 6's explicit exclusion of HR,
payroll, CRM, and other administration. No panel in this screen may show
anything outside capital/treasury:

```text
BUSINESS CAPITAL

Cash:                          £680,000
Required liquidity:            £300,000
Potential surplus:             £380,000
Current yield:                 2.1%
Comparable eligible options:   3.8–4.2%
FX exposure:                   USD £190,000 equivalent
Borrowing:                     £250,000 @ 6.4%
```

## 16. First Prototype Direction

Desktop-first, dark, professional — not a flashing-numbers dashboard.
Illustrative layout only (not final visual design):

```text
┌──────────────────────────────────────────────────┐
│ OptiFi                              Portfolio ▼   │
├──────────┬─────────────────────────────────────────┤
│ TODAY    │  GOOD MORNING                            │
│ Portfolio│  £428,600  Portfolio Value                │
│ Research │  Risk 6.3/10   Efficiency 84/100          │
│ Scenario │  3 THINGS MATTER TODAY                     │
│ Risk     │  1. UK rates — No action                  │
│ Ask AI   │  2. Semiconductor revisions — Positive     │
│          │  3. Cash opportunity — +£816/year          │
└──────────┴─────────────────────────────────────────┘
```

## 17. Known Gaps / Open Questions Carried to Phase 2C

1. Visual design (colour, typography, spacing, component library) is
   entirely out of scope here — Phase 2C or dedicated design work.
2. Whether `validation_status` is shown to all users by default, or only on
   demand via "Why?" — not decided here.
3. The Tier 3 referral CTA ("Find a qualified professional") — whether
   OptiFi maintains an actual referral network or just points to generic
   guidance — ties to `REGULATORY_BOUNDARIES.md` Section 6, item 5, and is
   moot in any case until Gate B clears.
4. How the Opportunity Feed orders/prioritises multiple simultaneous
   opportunities across tiers — not decided.
5. ~~Whether Scenario Lab is preset-only or free-form for MVP...~~
   **RESOLVED:** `SIMULATION_ENGINE_SPEC.md` Section 5 recommends
   preset-only for MVP — free-form scenario interpretation is
   substantially harder than propagating pre-vetted scenarios. This
   document's preset-only assumption is now grounded in that reasoning,
   not asserted for UX discipline alone.
6. Frontend technology to render any of this — Phase 2C
   (`FRONTEND_SPEC.md`).
