"""
GET /api/portfolio — APP_UX_BLUEPRINT.md Section 7. The user's full
balance sheet: assets, liabilities, allocation, sector/geographic/currency
exposure, concentration, liquidity, risk, performance. Current holdings
values are FACT; volatility/VaR/exposure figures are ESTIMATE — each
panel's figures keep their own `information_class`, never blended.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from optifi_ai.roadblock import check_staleness

from ..demo_portfolio import CASH_GBP, LIQUIDITY_TARGET_FRACTION, TECH_TARGET_MAX, US_TECH
from ..evidence_store import get_demo, serialize_uap

_FRESHNESS_MAX_AGE = timedelta(days=30)

router = APIRouter(tags=["portfolio"])


def _exposure_by(demo, key: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for h in demo.holdings:
        totals[getattr(h, key)] += h.weight
    return {k: round(v, 4) for k, v in totals.items()}


@router.get("/portfolio")
def get_portfolio(portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    demo = get_demo(portfolio)

    cash_holding = next(h for h in demo.holdings if h.entity_id == CASH_GBP)
    tech_holding = next(h for h in demo.holdings if h.entity_id == US_TECH)
    reserve = demo.assets_total * LIQUIDITY_TARGET_FRACTION

    stale_roadblocks = check_staleness(
        [*[h.fact_uap for h in demo.holdings], demo.stale_price_check_uap],
        datetime.now(timezone.utc),
        _FRESHNESS_MAX_AGE,
    )

    return {
        "portfolio_variant": portfolio,
        "assets_total": demo.assets_total,
        "liabilities_total": demo.liabilities_total,
        "net_capital": demo.net_capital,
        "liabilities": [serialize_uap(demo.mortgage_uap)],
        "data_freshness": {
            "checked_against_present_time": True,
            # roadblock.Roadblock.description is a diagnostic string
            # (ai-engine/roadblock.py, Phase E6) meant for logs, not
            # user-facing prose — it embeds Python repr() output for
            # datetimes/timedeltas. Reformatted here for display without
            # touching that already-tested module.
            "stale_items": [
                {
                    "kind": r.kind,
                    "description": f"'{r.subject}' has not been independently re-verified in over {_FRESHNESS_MAX_AGE.days} days.",
                    "subject": r.subject,
                }
                for r in stale_roadblocks
            ],
        },
        "holdings": [
            {
                "entity_id": h.entity_id,
                "label": h.label,
                "sector": h.sector,
                "geography": h.geography,
                "currency": h.currency,
                "weight": round(h.weight, 4),
                "value": round(h.value, 2),
                "fact": serialize_uap(h.fact_uap),
            }
            for h in demo.holdings
        ],
        "allocation": {h.label: round(h.weight, 4) for h in demo.holdings},
        "sector_exposure": _exposure_by(demo, "sector"),
        "geographic_exposure": _exposure_by(demo, "geography"),
        "currency_exposure": _exposure_by(demo, "currency"),
        "concentration": {
            "largest_holding": max(demo.holdings, key=lambda h: h.weight).label,
            "largest_weight": round(max(h.weight for h in demo.holdings), 4),
            "technology_target_max": TECH_TARGET_MAX,
            "technology_breach": tech_holding.weight > TECH_TARGET_MAX,
        },
        "liquidity": {
            "actual_cash": round(cash_holding.value, 2),
            "minimum_reserve": round(reserve, 2),
            "liquidity_efficiency": serialize_uap(demo.sub_efficiency_uaps["liquidity_efficiency"]),
        },
        "risk": {
            "covariance": serialize_uap(demo.covariance_uap),
            "portfolio_variance": serialize_uap(demo.variance_uap),
            "historical_var_95": serialize_uap(demo.historical_var_uap),
            "parametric_var_95": serialize_uap(demo.parametric_var_uap),
        },
        "performance": {
            "sharpe_ratio": serialize_uap(demo.sharpe_uap),
        },
        "capital_efficiency": {
            **serialize_uap(demo.capital_efficiency_uap),
            "sub_scores": {k: serialize_uap(v) for k, v in demo.sub_efficiency_uaps.items()},
        },
    }
