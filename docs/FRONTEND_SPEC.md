# FRONTEND_SPEC

**Status:** DRAFT (v1 — Phase E7)

## 1. Purpose & Scope

This document specifies OptiFi's first user-facing interface, built around
`APP_UX_BLUEPRINT.md`'s seven screens (Today, Portfolio, Opportunities,
Risk, Research, Scenario Lab, Ask OptiFi), the frontend technology
`APP_UX_BLUEPRINT.md` Section 17 item 6 and `SYSTEM_ARCHITECTURE.md` left
"TBD"/unspecified, and the `backend` API surface
`SYSTEM_ARCHITECTURE.md` Section 5 named but never built.

## 2. Relationship to Prior Documents

Implements `APP_UX_BLUEPRINT.md`'s screens and Section 3's standing UI
constraints exactly. Follows `SYSTEM_ARCHITECTURE.md` Section 6's
frontend/backend boundary: `frontend` renders `information_class`/
`validation_status` distinctions already resolved by the pipeline; it
computes or interprets none of them. `backend` fulfils Section 5's
technical-orchestration role by calling `ai-engine`'s Phase E6
`CIOOrchestrator` and the other specialist engines directly and packaging
their output as JSON — never re-deriving analytical logic of its own
beyond thin, clearly-labelled presentation transforms (Section 6 below).

## 3. Stack (previously "TBD")

- **Frontend:** React 19 + TypeScript + Vite, React Router 7, plain CSS
  (custom properties for the dark theme, no component library). Vitest +
  React Testing Library for tests.
- **Backend:** FastAPI (Python), own `.venv`/`pyproject.toml` matching
  every engine's existing pattern, depending on `optifi-shared`,
  `optifi-causal`, `optifi-forecast`, `optifi-evaluation`, `optifi-quant`,
  `optifi-simulation`, `optifi-optimisation`, `optifi-verification`,
  `optifi-ai`, and `optifi-replay` as editable installs.

Ordinary engineering choices, not architectural or financial-model
decisions — confirmed with the user before implementation, documented
here per the precedent `APP_UX_BLUEPRINT.md` Section 17 item 6 itself
anticipated ("Frontend technology to render any of this").

## 4. Data: One Illustrative Demo Portfolio, Never Fabricated Per-Request

No live data vendor and no real user accounts exist yet (README.md).
`backend/app/demo_portfolio.py` builds one illustrative demo dataset —
five holdings (UK Banks, UK Gilts, US Technology, EU Industrials, GBP
Cash) plus a mortgage liability, portfolio totals matching
`APP_UX_BLUEPRINT.md` Section 7's own worked example (£548,600 assets,
£120,000 liabilities, £428,600 net) — by calling real engine functions
over small, fixed, clearly-labelled synthetic series (never random),
exactly the discipline `replay-engine` and the vertical-slice integration
test already established. Every number on screen traces back to a real
computation; nothing is hand-typed UI dressing.

Two named variants, selected by the caller, never per-request randomness:
`"default"` genuinely breaches its technology-concentration and
liquidity targets (real opportunities exist); `"efficient"` sits within
every target (a real, non-fabricated "no opportunities" state). Selected
via the sidebar's "Demo portfolio" control, which stands in for account
selection until a real Financial Twin exists.

## 5. Routes / Screens

| Route | Screen | Backend endpoint(s) |
|---|---|---|
| `/` | Today | `GET /api/today` |
| `/portfolio` | Portfolio | `GET /api/portfolio` |
| `/opportunities` | Opportunities | `GET /api/opportunities` |
| `/risk` | Risk | `GET /api/risk` |
| `/research`, `/research/:assetId` | Research | `GET /api/research/{asset_id}` |
| `/scenario-lab` | Scenario Lab | `GET /api/scenarios`, `POST /api/scenarios/{id}/run` |
| `/ask` | Ask OptiFi | `POST /api/ask` |
| — | "Why?" drill-down (every screen) | `GET /api/evidence/{uap_id}` |

No Business Mode screen — this phase's own screen list (Today through Ask
OptiFi) omits it; deferred, see Section 9.

## 6. API / Data Contract

Every `UAP`-shaped field in a response is `UAP.model_dump(mode="json")`
verbatim (`backend/app/evidence_store.py:serialize_uap`) — the frontend's
TypeScript types (`frontend/src/api/types.ts`) mirror the real pydantic
shape field-for-field, with `information_class`/`validation_status`/
`confidence` as literal unions rather than `string`.

Two kinds of light, explicitly-labelled backend-side presentation
transforms exist, neither a new financial model:
- **Standard-formula readouts** computed directly in a router (e.g.
  `risk.py`'s variance-contribution decomposition over quant-engine's own
  covariance matrix; `today.py`'s 0-10 risk display scaling) — each
  UAP-wrapped, `ESTIMATE`/`PROVISIONAL`, with `producer` stating it is a
  backend-computed readout, not a specialist engine's own output.
- **`confidence_breakdown`** (`evidence_store.py`) — `APP_UX_BLUEPRINT.md`
  Section 13's structured confidence display, derived from real,
  already-present fields (`validation_status`, disagreement notes),
  never an invented number.

`POST /api/ask` wraps Phase E6's `CIOOrchestrator.answer_query` directly;
`GET /api/evidence/{id}` wraps `ai-engine`'s `trace_evidence`. Neither
route re-implements routing, roadblock detection, or the verification
gate — see `docs/CIO_ORCHESTRATION_SPEC.md`.

## 7. Component Hierarchy

```
App (nav shell + portfolio-variant selector, provides AppContext via Outlet)
├── TodayScreen
├── PortfolioScreen
├── OpportunitiesScreen
├── RiskScreen
├── ResearchScreen (asset picker when no :assetId, detail view otherwise)
├── ScenarioLabScreen
└── AskOptiFiScreen

components/shared/ (built once, composed by every screen)
├── InformationClassBadge   — FACT/ESTIMATE/JUDGEMENT, label+shape not colour alone
├── ValidationStatusFlag    — renders only when status !== VERIFIED
├── ConfidenceBadge         — expandable structured breakdown
├── WhyDrillDown            — lazy-fetches /api/evidence/:id, renders the vertical stepper
├── SuggestedActionPill / CallToActionButton — restricted to the non-directive vocabulary
└── LoadingState / ErrorState / EmptyState
```

`useApi` (`src/api/client.ts`) centralises loading/error/data state for
every screen — one real, tested implementation of "loading/error states"
rather than per-screen copy-paste.

## 8. Standing UI Constraints — How Each Is Enforced

Per `APP_UX_BLUEPRINT.md` Section 3:

- **No directive language.** `SuggestedAction`/`CallToAction` TS unions
  reject a bad literal at compile time; `SuggestedActionPill`/
  `CallToActionButton` reject an unrecognised runtime value rather than
  rendering it (a plain `fetch` response isn't type-checked at the
  network boundary, so the runtime guard is the real enforcement).
  `Ask OptiFi`'s `suggested_action` is free prose from `ai-engine`'s
  `build_explanation` (E6), not this fixed vocabulary — rendered as text,
  with directive-language redaction already enforced server-side
  (`explanation.py`'s `_redact_directive_language`).
- **No execution/transaction controls.** Structurally true — no route,
  button, or form anywhere in this codebase transfers money, places a
  trade, or mutates a real account.
- **FACT/ESTIMATE/JUDGEMENT always visually distinguishable; non-VERIFIED
  always flagged.** `InformationClassBadge`/`ValidationStatusFlag`,
  applied everywhere a UAP reaches the screen.
- **Capital Efficiency Score shown as computed, not opinion, and never
  authoritative while PROVISIONAL.** Today/Portfolio read
  `capital_efficiency.validation_status` (real field) to decide whether
  to append "(provisional — not authoritative)" — never hardcoded.
- **"No opportunity" is a valid, real state.** `OpportunitiesScreen`
  renders `EmptyState` with the backend's real
  `no_opportunities_message`, never a manufactured card.

## 9. Test Results

- **Backend:** 35/35 passing (`cd backend && .venv/bin/python -m pytest -q`)
  — one module per screen's router, covering: loading (implicit,
  synchronous), `PROVISIONAL` estimates, genuine disagreement/conflict
  (shared `disagreement_set_ref`), stale data (a deliberately-dated
  checkpoint, checked against present time), unavailable analysis
  (unmodelled scenario, unsupported asset), a real `REJECT`ed
  recommendation, `NO ACTION` default, and the real empty-opportunities
  state.
- **Frontend:** 25/25 passing (`cd frontend && npm test`), plus a clean
  `tsc -b` and `npm run build`. Covers: `InformationClassBadge`/
  `ValidationStatusFlag` rendering per state, `SuggestedActionPill`'s
  type-level (`@ts-expect-error`) and runtime rejection of a directive
  value, `WhyDrillDown`'s lazy fetch and real multi-hop chain rendering,
  `LoadingState`/`ErrorState`/`EmptyState`, and screen-level tests for
  `TodayScreen` (loading/error/provisional-not-authoritative) and
  `OpportunitiesScreen` (empty state and a populated card).
- **Visual verification:** both servers run locally
  (`uvicorn app.main:app` on :8000, `npm run dev` on :5173) and every
  screen — plus the no-opportunities, rejected-recommendation, unmodelled-
  scenario, unsupported-asset, and mobile-width states — was captured
  with a headless-Chromium script and reviewed frame by frame. This
  caught and fixed three real bugs no unit test had: `<details>` (used by
  `WhyDrillDown`) nested inside `<p>` in four screens (invalid HTML,
  browser-corrected DOM structure/hydration mismatch), a raw Python
  `repr()`-formatted string leaking into the Portfolio screen's data-
  freshness panel, and a mislabelled/unformatted VaR figure on the Risk
  screen.
- **Accessibility review (manual, no automated a11y tooling wired):**
  semantic landmarks (`<nav>`, headings), `LoadingState`/`ErrorState` use
  `role="status"`/`role="alert"`, `WhyDrillDown` is a native `<details>`
  (keyboard-operable, no custom ARIA needed), information-class
  distinctions use label text + distinct styling rather than colour
  alone, the mobile breakpoint collapses the sidebar to a horizontally-
  scrollable top tab bar. Not verified: contrast ratios against WCAG
  thresholds, full keyboard-only navigation walkthrough, screen-reader
  testing with a real AT — see Section 10.

## 10. Known Gaps / Open Questions

1. **No automated accessibility audit tool** (e.g. axe) is wired into
   either test suite — the review above is manual and visual only.
2. **`validation_status` default visibility** — shown by default
   throughout this implementation; `APP_UX_BLUEPRINT.md` Section 17 item 2
   leaves "default-visible vs. on-demand" open, unresolved here too.
3. **Opportunity Feed ordering across tiers** — `APP_UX_BLUEPRINT.md`
   Section 17 item 4 is still open; this implementation only has Tier 1
   opportunities to order (Tier 2/3 are deferred, Section 11), so the
   question doesn't yet have real cases to resolve against.
4. **Contrast ratios / WCAG conformance level** not measured against a
   formal standard.
5. **The backend-side "standard-formula readout" pattern** (Section 6) —
   whether risk-contribution decomposition and similar readouts should
   eventually move into `quant-engine` itself as first-class functions,
   rather than living in `backend`, is a real design question this phase
   does not resolve.

## 11. Intentionally Deferred

- **Business Mode screen** (`APP_UX_BLUEPRINT.md` Section 15) — outside
  this phase's seven-screen list.
- **Tier 2 (general tax/estate education) and Tier 3 (flag-only
  structuring) Opportunity cards** — gated on `MVP_ROADMAP.md` Gate A/Gate
  B, neither cleared; not built even as inert mockups in this pass.
- **A real LLM/NLU provider** behind `Ask OptiFi` — unchanged from Phase
  E6; `ai-engine` still only has `StubExplanationGenerator`.
- **Free-form scenario queries in Scenario Lab** — preset-only, per
  `SIMULATION_ENGINE_SPEC.md` Section 5's already-resolved recommendation.
- **Full portfolio-risk recomputation in Research's "[Asset] + You"**
  panel — shows exposure-percentage deltas only; a real re-optimisation
  preview is explicitly flagged as out of scope in that panel's own
  response (`asset_plus_you.limitations`).
