"""
FastAPI app — backend's technical orchestration layer (SYSTEM_ARCHITECTURE.md
Section 5). Sequences real engine calls (via demo_portfolio.py/evidence_store.py)
and packages Stage 13 output as JSON for `frontend` to render. No analytical
logic lives in `frontend` — every FACT/ESTIMATE/JUDGEMENT distinction and
every validation_status arrives here already resolved.

No execution/trade capability anywhere in this app (this phase's own "No
Execution" section) — there is no route that transfers money, places a
trade, or mutates a real account; every mutating-looking action a screen
might imply is DEMONSTRATIONAL and confined to a preset scenario
computation, never a real transaction.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import ask, evidence, opportunities, portfolio, research, risk, scenarios, today

app = FastAPI(title="OptiFi backend (MVP)", version="0.1.0")

# Local-dev-only: the Vite dev server runs on a different port. No
# deployment/production CORS policy is decided here (SYSTEM_ARCHITECTURE.md
# Section 7 leaves deployment architecture unspecified).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(today.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(opportunities.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(ask.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
