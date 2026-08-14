"""
GET /api/research/{asset_id} — APP_UX_BLUEPRINT.md Section 8. Current
factual state, forecasts, scenarios, risk, causal exposures, news/events,
then "[Asset] + You" — how the asset would affect the user's existing
portfolio. An asset outside the demo universe (never fabricated coverage)
returns a structured, honest "not covered" response — the deliberate
"unavailable analysis" test case.
"""

from __future__ import annotations

import statistics

from fastapi import APIRouter, Query

from optifi_forecast import exponential_smoothing_forecast
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from ..demo_portfolio import RETURNS_BY_ENTITY
from ..evidence_store import confidence_breakdown, get_demo, serialize_uap

router = APIRouter(tags=["research"])


@router.get("/research/{asset_id}")
def get_research(asset_id: str, portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    demo = get_demo(portfolio)
    holding = next((h for h in demo.holdings if h.entity_id == asset_id), None)

    if holding is None:
        return {
            "asset_id": asset_id,
            "covered": False,
            "message": (
                "No analytical coverage exists for this asset in the current demo "
                "portfolio — nothing is fabricated in its place."
            ),
        }

    returns = RETURNS_BY_ENTITY[asset_id]
    forecast_value = exponential_smoothing_forecast(returns)
    forecast_uap = UAP(
        subject=f"{holding.label} — next-period return forecast",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=forecast_value,
        source="computed from the demo portfolio's illustrative monthly return history",
        producer="forecast-engine / exponential_smoothing_forecast",
        confidence=ConfidenceLevel.MODERATE,
        generated_at=demo.now,
    )
    std_dev = statistics.pstdev(returns)
    risk_uap = UAP(
        subject=f"{holding.label} — return volatility (monthly std dev)",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=round(std_dev, 5),
        source="computed from the demo portfolio's illustrative monthly return history",
        producer="backend / sample standard deviation",
        confidence=ConfidenceLevel.MODERATE,
    )

    causal_claims = [c for c in demo.causal_claims if c.effect_entity_id == asset_id]
    scenario_result = demo.rate_cut_scenario_results.get(asset_id)

    hypothetical_addition = 10_000.0
    new_assets_total = demo.assets_total + hypothetical_addition
    exposure_after = (holding.value + hypothetical_addition) / new_assets_total

    uaps_for_confidence = [holding.fact_uap, forecast_uap] + causal_claims
    return {
        "asset_id": asset_id,
        "covered": True,
        "label": holding.label,
        "current_state": serialize_uap(holding.fact_uap),
        "fundamentals": {
            "note": "No live fundamentals feed connected — see DATA_SOURCE_REGISTRY.md; not fabricated."
        },
        "forecasts": [serialize_uap(forecast_uap)],
        "scenarios": {asset_id: serialize_uap(scenario_result)} if scenario_result else {},
        "risk": serialize_uap(risk_uap),
        "causal_exposures": [serialize_uap(c) for c in causal_claims],
        "news_events": {"note": "No live news/events feed connected — see DATA_SOURCE_REGISTRY.md; not fabricated."},
        "asset_plus_you": {
            "current_portfolio_exposure": round(holding.weight, 4),
            "if_10000_invested": {
                "additional_amount": hypothetical_addition,
                "exposure_after": round(exposure_after, 4),
            },
            "sector_exposure": {"current": round(holding.weight, 4)},
            "limitations": [
                "portfolio-level risk/optimisation impact of this hypothetical "
                "addition is not recomputed here — showing that would require "
                "re-running covariance/optimisation over the changed weights, "
                "out of scope for this research view"
            ],
        },
        "confidence": confidence_breakdown(uaps_for_confidence),
    }
