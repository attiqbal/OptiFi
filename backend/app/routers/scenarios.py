"""
GET /api/scenarios, POST /api/scenarios/{id}/run — APP_UX_BLUEPRINT.md
Section 10. Preset-only (SIMULATION_ENGINE_SPEC.md Section 5's own
recommendation, already resolved per that document's Section 17 item 5) —
the full seven-scenario library is listed, but only `rates_cut_100bp` has
a real causal pathway/sensitivity registered against this demo portfolio
(`demo_portfolio.py`). Running any other preset returns a structured
"not modelled" response rather than fabricating a result — the deliberate
"unavailable analysis" case this phase's Testing section asks for.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from optifi_simulation.scenario_library import get_scenario, SCENARIO_LIBRARY

from ..demo_portfolio import RATES_CUT_100BP
from ..evidence_store import confidence_breakdown, get_demo, serialize_uap

router = APIRouter(tags=["scenarios"])

_RUNNABLE_SCENARIO_IDS = {RATES_CUT_100BP.scenario_id}


@router.get("/scenarios")
def list_scenarios() -> dict:
    return {
        "scenarios": [
            {
                "scenario_id": s.scenario_id,
                "family": s.family,
                "description": s.description,
                "horizon": s.horizon,
                "runnable_against_demo_portfolio": s.scenario_id in _RUNNABLE_SCENARIO_IDS,
            }
            for s in SCENARIO_LIBRARY
        ]
    }


@router.post("/scenarios/{scenario_id}/run")
def run_scenario(scenario_id: str, portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    try:
        scenario = get_scenario(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario id {scenario_id!r}.")

    demo = get_demo(portfolio)

    if scenario_id not in _RUNNABLE_SCENARIO_IDS:
        return {
            "scenario_id": scenario_id,
            "available": False,
            "message": (
                "This scenario is not yet modelled against the demo portfolio — "
                "no causal pathway or sensitivity estimate has been registered "
                "for it. No result is fabricated."
            ),
        }

    results = demo.rate_cut_scenario_results
    impact = demo.rate_sensitive_impact_uap
    winners = sorted(
        results.items(), key=lambda kv: kv[1].base_case, reverse=True
    )
    uaps = list(results.values()) + [impact]

    return {
        "scenario_id": scenario_id,
        "available": True,
        "assumptions": {
            "description": scenario.description,
            "perturbed_entity_id": scenario.perturbed_entity_id,
            "magnitude": scenario.perturbation_magnitude,
            "unit": scenario.unit,
            "horizon": scenario.horizon,
        },
        "affected_variables": list(results.keys()),
        "portfolio_distribution": {
            "base_case": impact.result["portfolio_base_case"],
            "range_low": impact.result["range_low"],
            "range_high": impact.result["range_high"],
            "contributions": impact.result["contributions"],
        },
        "winners": winners[0][0] if winners[0][1].base_case > 0 else None,
        "losers": winners[-1][0] if winners[-1][1].base_case < 0 else None,
        "per_entity_results": {entity_id: serialize_uap(r) for entity_id, r in results.items()},
        "uncertainties": sorted({f for r in results.values() for f in r.sensitivity_factors}),
        "confidence": confidence_breakdown(uaps),
        "portfolio_impact_uap": serialize_uap(impact),
    }
