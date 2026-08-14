"""
GET /api/opportunities — APP_UX_BLUEPRINT.md Section 6. Only analytically
supported opportunities; "no opportunities" is a valid, real state (the
"efficient" demo variant genuinely produces one — never manufactured to
fill space).
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..demo_portfolio import CASH_GBP, LIQUIDITY_TARGET_FRACTION, TECH_TARGET_MAX, US_TECH
from ..evidence_store import confidence_breakdown, get_demo, serialize_uap

router = APIRouter(tags=["opportunities"])


def _idle_cash_opportunity(demo) -> dict | None:
    holding = next(h for h in demo.holdings if h.entity_id == CASH_GBP)
    reserve = demo.assets_total * LIQUIDITY_TARGET_FRACTION
    idle = holding.value - reserve
    if idle <= 0:
        return None
    achieved_yield, comparable_yield = 0.018, 0.045
    annual_opportunity = idle * (comparable_yield - achieved_yield)
    uaps = [holding.fact_uap, demo.sub_efficiency_uaps["cash_efficiency"]]
    return {
        "kind": "excess_idle_cash",
        "headline": f"£{annual_opportunity:,.0f}/year opportunity",
        "description": (
            f"Your cash reserve exceeds your selected liquidity requirement by "
            f"£{idle:,.0f}. Eligible alternatives currently provide higher expected yield."
        ),
        "fact": serialize_uap(holding.fact_uap),
        "estimates": [serialize_uap(demo.sub_efficiency_uaps["cash_efficiency"])],
        "call_to_action": "Review",
        "confidence": confidence_breakdown(uaps),
        "evidence_ids": [u.id for u in uaps],
    }


def _concentration_opportunity(demo) -> dict | None:
    holding = next(h for h in demo.holdings if h.entity_id == US_TECH)
    if holding.weight <= TECH_TARGET_MAX:
        return None
    uaps = [holding.fact_uap]
    return {
        "kind": "concentration",
        "headline": "Portfolio concentration",
        "description": (
            f"Technology exposure is {holding.weight * 100:.0f}%. "
            f"Your target maximum: {TECH_TARGET_MAX * 100:.0f}%."
        ),
        "fact": serialize_uap(holding.fact_uap),
        "estimates": [],
        "call_to_action": "Analyse",
        "confidence": confidence_breakdown(uaps),
        "evidence_ids": [u.id for u in uaps],
    }


@router.get("/opportunities")
def get_opportunities(portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    demo = get_demo(portfolio)
    opportunities = [
        o for o in (_idle_cash_opportunity(demo), _concentration_opportunity(demo)) if o is not None
    ]
    return {
        "portfolio_variant": portfolio,
        "opportunities": opportunities,
        "no_opportunities_message": (
            "No new opportunities today. Your capital allocation remains efficient "
            "against your current mandate."
        )
        if not opportunities
        else None,
    }
