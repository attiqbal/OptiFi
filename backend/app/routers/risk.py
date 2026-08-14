"""
GET /api/risk — APP_UX_BLUEPRINT.md Section 7's risk panels, expanded into
their own screen per this phase's Risk screen brief: major risk
contributors, concentration, volatility, drawdown scenarios, FX, duration,
scenario sensitivity.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from ..demo_portfolio import CASH_GBP, UK_GILTS
from ..evidence_store import get_demo, serialize_uap

router = APIRouter(tags=["risk"])

# Illustrative modified duration by holding — only UK Gilts carries
# meaningful rate duration in this demo universe; every other holding is
# treated as ~0 for this simplified, clearly-labelled display metric.
_MODIFIED_DURATION_BY_ENTITY = {UK_GILTS: 7.0}


def _risk_contributions(demo) -> UAP:
    """Standard variance-contribution decomposition
    (contribution_i = w_i * (Sigma . w)_i / portfolio_variance) over
    quant-engine's own covariance matrix and portfolio_variance — a
    textbook readout of already-produced ESTIMATE output, not a new
    financial model. Backend-computed and labelled as such, same
    transparency discipline as `today.py`'s risk-score scaling."""
    weights = {h.entity_id: h.weight for h in demo.holdings}
    cov = demo.covariance_uap.result
    variance = demo.variance_uap.result
    contributions = {}
    for i in weights:
        sigma_w_i = sum(cov[i][j] * weights[j] for j in weights)
        contributions[i] = (weights[i] * sigma_w_i) / variance if variance else 0.0
    total = sum(contributions.values()) or 1.0
    normalised = {k: round(v / total, 4) for k, v in contributions.items()}
    return UAP(
        subject="risk contribution by holding",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=normalised,
        source="standard variance-contribution decomposition over quant-engine's covariance matrix",
        producer="backend / risk-contribution decomposition (standard formula, not a new model)",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=[demo.covariance_uap.id, demo.variance_uap.id],
    )


def _portfolio_duration(demo) -> UAP:
    weighted = sum(h.weight * _MODIFIED_DURATION_BY_ENTITY.get(h.entity_id, 0.0) for h in demo.holdings)
    return UAP(
        subject="portfolio modified duration (illustrative)",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=round(weighted, 2),
        source="weighted duration over the demo holdings' illustrative modified durations",
        producer="backend / duration aggregation",
        confidence=ConfidenceLevel.LOW,
        limitations=["only UK Gilts carries a modelled duration in this demo universe"],
    )


@router.get("/risk")
def get_risk(portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    demo = get_demo(portfolio)
    fx_exposure = {
        h.currency: round(h.weight, 4)
        for h in demo.holdings
        if h.currency != "GBP"
    }

    return {
        "portfolio_variant": portfolio,
        "risk_contributors": serialize_uap(_risk_contributions(demo)),
        "concentration": {
            "largest_holding": max(demo.holdings, key=lambda h: h.weight).label,
            "largest_weight": round(max(h.weight for h in demo.holdings), 4),
        },
        "volatility": {
            "portfolio_variance": serialize_uap(demo.variance_uap),
            "portfolio_std_dev": round(demo.variance_uap.result**0.5, 6),
        },
        "drawdown_scenarios": {
            "historical_var_95": serialize_uap(demo.historical_var_uap),
            "parametric_var_95": serialize_uap(demo.parametric_var_uap),
            "rate_cut_scenario": serialize_uap(demo.rate_sensitive_impact_uap),
        },
        "fx_exposure": fx_exposure,
        "duration": serialize_uap(_portfolio_duration(demo)),
        "scenario_sensitivity": {
            entity_id: serialize_uap(result) for entity_id, result in demo.rate_cut_scenario_results.items()
        },
    }
