# backend

FastAPI technical orchestration / JSON API (`SYSTEM_ARCHITECTURE.md`
Section 5, `docs/FRONTEND_SPEC.md` Section 6, Phase E7).

**Implemented:**
- One illustrative demo portfolio (`app/demo_portfolio.py`), built from
  real engine calls over small, fixed, synthetic series — never random,
  never hand-typed UI dressing. Two variants (`default`/`efficient`)
  selected explicitly, not per-request randomness.
- Eight route modules under `app/routers/`, one per `APP_UX_BLUEPRINT.md`
  screen plus `/api/evidence/{id}` for the "Why?" drill-down, wrapping
  real specialist-engine functions and Phase E6's `CIOOrchestrator`
  directly — no analytical logic reimplemented here beyond two clearly-
  labelled, documented "standard-formula readout" transforms (a risk-
  contribution decomposition, a display-only risk score scaling).
- 35 automated tests covering the real states `docs/FRONTEND_SPEC.md`
  Section 9 lists: stale data, PROVISIONAL estimates, genuine
  disagreement, a real REJECTed recommendation, the real empty-
  opportunities state, and unavailable analysis (unmodelled scenario,
  unsupported asset).

**Not yet implemented:**
- A live data vendor connection — everything here is the same
  illustrative/synthetic data every other phase has used.
- Real user accounts, a Financial Twin, or per-user portfolios — one
  fixed illustrative demo portfolio stands in for all of these.
- Any deployment configuration — this runs locally only
  (`uvicorn app.main:app`).

Run locally: `.venv/bin/uvicorn app.main:app --port 8000` (after
`.venv/bin/pip install -e ".[dev]"`). Tests: `.venv/bin/python -m pytest -q`.
