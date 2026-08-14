"""
GET /api/today — APP_UX_BLUEPRINT.md Section 5. Not a dashboard, a
briefing: portfolio value, risk, capital efficiency (never shown as
authoritative while PROVISIONAL — Phase E7 brief), and the material
developments that genuinely apply to this variant (never padded to a
fixed count of 3 — "no opportunity is a valid state" extends naturally to
"no third development exists" too).
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from optifi_ai.explanation import build_explanation
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from ..demo_portfolio import TECH_TARGET_MAX, US_TECH
from ..evidence_store import confidence_breakdown, get_demo, serialize_uap

router = APIRouter(tags=["today"])


def _risk_score_uap(demo) -> UAP:
    # DESIGNED display scaling (not a QUANT_ENGINE_SPEC.md formula) —
    # maps parametric VaR at a 3%-of-assets illustrative reference point
    # to a 0-10 display score. Documented as illustrative, matching the
    # transparency discipline quant-engine's own DESIGNED sub-scores use.
    reference = demo.assets_total * 0.03
    score = min(10.0, (demo.parametric_var_uap.result / reference) * 6.0)
    return UAP(
        subject="portfolio risk score (0-10 display scaling)",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=round(score, 1),
        source="derived from quant-engine's parametric VaR",
        producer="backend / DESIGNED display scaling, not a QUANT_ENGINE_SPEC.md formula",
        confidence=ConfidenceLevel.LOW,
        dependencies=[demo.parametric_var_uap.id],
        limitations=["illustrative 0-10 display mapping, not an authoritative risk figure"],
    )


def _rate_development(demo) -> dict:
    uaps = [demo.causal_claims[0], demo.causal_claims[1], demo.rate_sensitive_impact_uap]
    explanation = build_explanation(uaps)
    base_case = demo.rate_sensitive_impact_uap.result["portfolio_base_case"]
    impact = "Positive" if base_case > 0.005 else ("Negative" if base_case < -0.005 else "Negligible")
    return {
        "headline": "UK interest-rate expectations changed",
        "fact": None,
        "estimates": [serialize_uap(u) for u in uaps],
        "judgement": None,
        "portfolio_impact": impact,
        "affected": ["UK Gilts", "UK Banks"],
        "suggested_action": "MONITOR" if impact != "Negligible" else "NO ACTION",
        "confidence": confidence_breakdown(uaps, explanation.disagreement_notes),
        "evidence_ids": [u.id for u in uaps],
    }


def _tech_concentration_development(demo) -> dict | None:
    holding = next(h for h in demo.holdings if h.entity_id == US_TECH)
    if holding.weight <= TECH_TARGET_MAX:
        return None
    uaps = [holding.fact_uap]
    return {
        "headline": "Technology concentration above target",
        "fact": serialize_uap(holding.fact_uap),
        "estimates": [],
        "judgement": None,
        "portfolio_impact": "Moderate",
        "affected": ["US Technology"],
        "your_exposure": round(holding.weight * 100, 1),
        "suggested_action": "REVIEW",
        "confidence": confidence_breakdown(uaps),
        "evidence_ids": [u.id for u in uaps],
    }


def _idle_cash_development(demo) -> dict | None:
    from ..demo_portfolio import CASH_GBP, LIQUIDITY_TARGET_FRACTION

    holding = next(h for h in demo.holdings if h.entity_id == CASH_GBP)
    reserve = demo.assets_total * LIQUIDITY_TARGET_FRACTION
    idle = holding.value - reserve
    if idle <= 0:
        return None
    achieved_yield, comparable_yield = 0.018, 0.045
    potential_annual_improvement = idle * (comparable_yield - achieved_yield)
    uaps = [holding.fact_uap, demo.sub_efficiency_uaps["cash_efficiency"]]
    return {
        "headline": f"£{idle:,.0f} idle cash detected",
        "fact": serialize_uap(holding.fact_uap),
        "estimates": [serialize_uap(demo.sub_efficiency_uaps["cash_efficiency"])],
        "judgement": None,
        "portfolio_impact": "Opportunity cost",
        "potential_annual_improvement": round(potential_annual_improvement, 0),
        "suggested_action": "REVIEW",
        "confidence": confidence_breakdown(uaps),
        "evidence_ids": [u.id for u in uaps],
    }


@router.get("/today")
def get_today(portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    demo = get_demo(portfolio)

    developments = [_rate_development(demo)]
    for builder in (_tech_concentration_development, _idle_cash_development):
        d = builder(demo)
        if d is not None:
            developments.append(d)

    ces_authoritative = demo.capital_efficiency_uap.validation_status == ValidationStatus.VERIFIED

    return {
        "portfolio_variant": portfolio,
        "portfolio_value": serialize_uap(
            UAP(
                subject="net capital",
                information_class=InformationClass.FACT,
                validation_status=ValidationStatus.VERIFIED,
                result=demo.net_capital,
                source="illustrative demo portfolio — not a real user account",
                producer="backend / demo-portfolio",
                confidence=ConfidenceLevel.HIGH,
                generated_at=demo.now,
            )
        ),
        "risk": serialize_uap(_risk_score_uap(demo)),
        "capital_efficiency": {
            **serialize_uap(demo.capital_efficiency_uap),
            "authoritative": ces_authoritative,
        },
        "developments": developments,
    }
