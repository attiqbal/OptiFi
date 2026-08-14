# frontend

React 19 + TypeScript + Vite UI implementing all seven
`APP_UX_BLUEPRINT.md` screens (Today, Portfolio, Opportunities, Risk,
Research, Scenario Lab, Ask OptiFi) against `backend`'s JSON API. See
`docs/FRONTEND_SPEC.md` for the full architecture, route table, component
hierarchy, and known gaps.

**Implemented:**
- All seven screens, each a thin composition of shared components
  (`src/components/shared/`) over `backend` responses — no analytical
  logic here (`SYSTEM_ARCHITECTURE.md` Section 6): `information_class`,
  `validation_status`, and every figure shown arrive already resolved.
- `InformationClassBadge`, `ValidationStatusFlag`, `ConfidenceBadge`,
  `WhyDrillDown` (the "Why?" evidence-trace drill-down), and
  `SuggestedActionPill`/`CallToActionButton` — the latter two restricted
  to `APP_UX_BLUEPRINT.md` Section 3's non-directive vocabulary at both
  the TypeScript type level and at runtime.
- 25 automated tests (Vitest + React Testing Library); a clean `tsc -b`
  and `npm run build`.

**Not yet implemented:**
- Any real account/authentication flow — a "Demo portfolio" selector
  (`default`/`efficient`) stands in for account selection.
- Automated accessibility auditing (manual review only — see
  `docs/FRONTEND_SPEC.md` Section 9/10).
- A Business Mode screen — outside this phase's seven-screen scope.

Run locally: `npm run dev` (expects `backend` running on
`http://localhost:8000`). Tests: `npm test`. Build: `npm run build`.
