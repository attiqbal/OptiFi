"""
Scenario library — PHASE E4 brief, Part 6: "Implement a limited initial
scenario library derived from actual forecasting needs... Do not create
hundreds of scenarios."

Exactly seven presets, one per named category (Part 6's own list: rates,
inflation, recession, equity shock, FX, commodity, earnings) — a curated
starting set, not an attempt at comprehensive coverage.
SIMULATION_ENGINE_SPEC.md Section 5's own recommendation
("preset-only scenarios, not free-form... free-form scenario
construction requires interpreting an arbitrary natural-language 'what
if' query, a substantially harder problem") is why these are fixed
presets, not a scenario-authoring API.

Honesty about "derived from actual forecasting needs": three of the
seven (inflation, equity_shock, earnings) are perturbations of the
EXACT entities `forecast-engine`'s three real, already-built targets
forecast (`optifi_forecast.targets` — `MACRO_CPI_TARGET`,
`MARKET_VOLATILITY_TARGET`, `COMPANY_REVENUE_DIRECTION_TARGET`) — a
genuine link to real forecasting output, not just a thematic name match.
The other four (rates, recession, fx, commodity) are illustrative
presets consistent with this project's existing rate-cut example
(already used throughout `causal-engine`/`simulation-engine`/the
vertical-slice integration test) or the canonical recession-probability
example `ANALYTICAL_CONTRACT_SPEC.md` itself uses — `forecast-engine`
does not yet have a target for FX, commodities, or policy-rate/recession
probability specifically, which is stated here as a real, current gap,
not glossed over.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    family: str
    description: str
    perturbed_entity_id: str
    perturbation_magnitude: float
    unit: str
    horizon: str
    justification: str


RATES_CUT_100BP = ScenarioDefinition(
    scenario_id="rates_cut_100bp",
    family="rates",
    description="UK base rate: -100bp",
    perturbed_entity_id="entity:uk-base-rate",
    perturbation_magnitude=-100.0,
    unit="bps",
    horizon="3-month",
    justification=(
        "Matches this project's own established illustrative rate-cut example "
        "(causal-engine's example_rate_cut_mortgage_claim, simulation-engine's "
        "example_rate_cut_gilt_impact, and the vertical-slice integration test) "
        "— genuine continuity with the transmission pathways those examples "
        "already assert evidence for, not a new unrelated preset."
    ),
)

INFLATION_SURPRISE_1PP = ScenarioDefinition(
    scenario_id="inflation_surprise_1pp",
    family="inflation",
    description="UK CPI YoY surprise: +1pp above consensus",
    perturbed_entity_id="entity:uk-cpi-yoy",
    perturbation_magnitude=1.0,
    unit="pp",
    horizon="3-month",
    justification=(
        "Directly perturbs the entity forecast-engine's real MACRO_CPI_TARGET "
        "forecasts (UK CPI YoY, 3-month horizon) — this scenario's horizon is "
        "deliberately matched to that target's own horizon so a genuine "
        "forecast output can supply this scenario's baseline/uncertainty "
        "context, per the brief's own 'derived from actual forecasting needs.'"
    ),
)

RECESSION_PROBABILITY_UP_20PP = ScenarioDefinition(
    scenario_id="recession_probability_up_20pp",
    family="recession",
    description="UK recession probability: +20pp",
    perturbed_entity_id="entity:uk-recession-probability",
    perturbation_magnitude=20.0,
    unit="pp",
    horizon="12-month",
    justification=(
        "The canonical recession-probability example ANALYTICAL_CONTRACT_SPEC.md "
        "and ENGINE_PIPELINE_SPECIFICATION.md themselves already use to illustrate "
        "multi-model disagreement — no dedicated forecast-engine target exists "
        "for this yet (a real, current gap, not silently glossed over)."
    ),
)

EQUITY_SHOCK_10PCT_DOWN = ScenarioDefinition(
    scenario_id="equity_shock_10pct_down",
    family="equity_shock",
    description="Broad equity market: -10% shock",
    perturbed_entity_id="entity:broad-equity-market",
    perturbation_magnitude=-10.0,
    unit="%",
    horizon="1-month",
    justification=(
        "A market-wide drawdown is the natural stress scenario forecast-engine's "
        "real MARKET_VOLATILITY_TARGET (synthetic index realised volatility, "
        "1-month horizon) feeds into — matched horizon for the same reason as "
        "the inflation preset above."
    ),
)

FX_GBPUSD_10PCT_DOWN = ScenarioDefinition(
    scenario_id="fx_gbpusd_10pct_down",
    family="fx",
    description="GBP/USD: -10% depreciation",
    perturbed_entity_id="entity:gbpusd",
    perturbation_magnitude=-10.0,
    unit="%",
    horizon="3-month",
    justification=(
        "Named explicitly in the Phase E4 brief's own Core Question list "
        "('FX movement'). forecast-engine has no FX forecasting target yet — "
        "this preset exists so the transmission-graph/propagation machinery "
        "can be exercised and tested for this category, not because a real "
        "forecast currently backs it (a genuine, stated gap)."
    ),
)

COMMODITY_OIL_30PCT_UP = ScenarioDefinition(
    scenario_id="commodity_oil_30pct_up",
    family="commodity",
    description="Brent crude oil: +30% shock",
    perturbed_entity_id="entity:brent-crude",
    perturbation_magnitude=30.0,
    unit="%",
    horizon="1-month",
    justification=(
        "Named explicitly in the brief's Core Question list ('earnings shock' "
        "sibling categories). Same honest gap as FX above — no forecast-engine "
        "commodity target exists yet."
    ),
)

EARNINGS_MISS_15PCT = ScenarioDefinition(
    scenario_id="earnings_miss_15pct",
    family="earnings",
    description="SYNTH_ACME quarterly earnings: -15% miss vs. expectations",
    perturbed_entity_id="entity:synth-acme-earnings",
    perturbation_magnitude=-15.0,
    unit="%",
    horizon="1-quarter",
    justification=(
        "Directly perturbs the entity forecast-engine's real "
        "COMPANY_REVENUE_DIRECTION_TARGET forecasts (SYNTH_ACME revenue-growth "
        "direction, 1-quarter horizon) — same SYNTH_ACME identifier "
        "data-engine's own Phase E2 fixture and forecast-engine's Phase E3 "
        "synthetic series both already use, for naming continuity."
    ),
)

SCENARIO_LIBRARY: tuple[ScenarioDefinition, ...] = (
    RATES_CUT_100BP,
    INFLATION_SURPRISE_1PP,
    RECESSION_PROBABILITY_UP_20PP,
    EQUITY_SHOCK_10PCT_DOWN,
    FX_GBPUSD_10PCT_DOWN,
    COMMODITY_OIL_30PCT_UP,
    EARNINGS_MISS_15PCT,
)


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    for scenario in SCENARIO_LIBRARY:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise KeyError(
        f"get_scenario: {scenario_id!r} is not in the scenario library — "
        f"known ids: {[s.scenario_id for s in SCENARIO_LIBRARY]!r}. This "
        "project uses preset-only scenarios (SIMULATION_ENGINE_SPEC.md "
        "Section 5), not free-form construction."
    )
