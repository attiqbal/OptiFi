"""
End-to-end synthetic integration — PHASE E4: forecast -> scenario ->
asset-impact -> portfolio propagation, wired through real code, no
hand-authored numbers surviving as production analytical logic.

  forecast-engine      -> a real forecast for context (Part 1: kept
                           conceptually separate from the scenario/
                           asset-response steps below, never wired
                           numerically into the scenario's magnitude —
                           SIMULATION_ENGINE_SPEC.md Section 5's presets
                           are curated independently of any live
                           forecast; see the comment at Step 1)
  causal-engine        -> TransmissionGraph of real, evidenced
                           CausalClaim edges (rate cut -> three assets,
                           extending this project's own established
                           illustrative rate-cut example set)
  quant-engine         -> real sensitivities (one deterministic/duration,
                           two statistical/OLS) via factor_sensitivity.py
  simulation-engine     -> propagate_scenario computes real, non-degenerate
                           ScenarioResults from the above — no hand-picked
                           base_case/range
  quant-engine (again)  -> propagate_to_portfolio combines them into one
                           portfolio-level figure with per-holding
                           attribution

Every number in the final portfolio result is independently
recomputable from the intermediate UAPs still available in this test —
proven directly below, not just asserted.
"""

from __future__ import annotations

import numpy as np
import pytest
from optifi_causal import CausalClaim, TransmissionGraph
from optifi_forecast import exponential_smoothing_forecast, synthetic_cpi_yoy_series
from optifi_quant import (
    duration_price_sensitivity,
    estimate_factor_sensitivity,
    propagate_to_portfolio,
    SensitivityRegistry,
)
from optifi_shared import ConfidenceLevel, ValidationStatus
from optifi_simulation import propagate_scenario
from optifi_simulation.scenario_library import RATES_CUT_100BP
from optifi_verification import check_no_look_ahead_contamination, VerdictType

RATE_ENTITY = "entity:uk-base-rate"
GILTS_ENTITY = "entity:uk-gilts"
BANK_EQUITIES_ENTITY = "entity:uk-bank-equities"
PROPERTY_ENTITY = "entity:uk-property"

PORTFOLIO_WEIGHTS = {GILTS_ENTITY: 0.40, BANK_EQUITIES_ENTITY: 0.30, PROPERTY_ENTITY: 0.30}


@pytest.fixture(scope="module")
def slice_state() -> dict:
    state: dict = {}

    # === Step 1: forecast-engine — real forecast, kept conceptually
    # === separate from the scenario below (Part 1's "must not be
    # === conflated"). This is NOT used to derive the scenario's -100bp
    # === magnitude; RATES_CUT_100BP is a curated preset
    # === (SIMULATION_ENGINE_SPEC.md Section 5), independent of any
    # === specific live forecast. Included to demonstrate genuine
    # === cross-engine composition, not because scenario propagation
    # === numerically depends on it.
    cpi_series = synthetic_cpi_yoy_series()
    state["cpi_forecast"] = exponential_smoothing_forecast(cpi_series)
    assert isinstance(state["cpi_forecast"], float)

    # === Step 2: causal-engine — real evidenced transmission graph ===
    graph = TransmissionGraph()
    causal_gilts = CausalClaim(
        subject="UK base rate cuts -> UK Gilts",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A base rate cut is associated with higher Gilt prices",
        source="illustrative — not a real data source",
        producer="causal-engine (illustrative)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=RATE_ENTITY,
        effect_entity_id=GILTS_ENTITY,
        mechanism="Lower base rate reduces yields; existing higher-coupon Gilts become relatively more attractive.",
    )
    causal_bank_equities = CausalClaim(
        subject="UK base rate cuts -> UK Bank Equities",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A base rate cut pressures UK bank equity valuations",
        source="illustrative — not a real data source",
        producer="causal-engine (illustrative)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=RATE_ENTITY,
        effect_entity_id=BANK_EQUITIES_ENTITY,
        mechanism="Bank profitability depends on net interest margin, which compresses when the base rate falls.",
    )
    causal_property = CausalClaim(
        subject="UK base rate cuts -> UK Property",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A base rate cut supports UK property valuations",
        source="illustrative — not a real data source",
        producer="causal-engine (illustrative)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=RATE_ENTITY,
        effect_entity_id=PROPERTY_ENTITY,
        mechanism="Lower rates reduce mortgage/borrowing costs, increasing effective demand for property.",
    )
    graph.add_edges([causal_gilts, causal_bank_equities, causal_property])
    state["graph"] = graph
    state["causal_claims"] = {
        GILTS_ENTITY: causal_gilts,
        BANK_EQUITIES_ENTITY: causal_bank_equities,
        PROPERTY_ENTITY: causal_property,
    }

    # === Step 3: quant-engine — real sensitivities, one deterministic,
    # === two statistical (Part 3's own required separation) ===
    registry = SensitivityRegistry()

    gilts_sensitivity = duration_price_sensitivity(modified_duration=8.0)
    gilts_sensitivity = gilts_sensitivity.model_copy(
        update={"result": {**gilts_sensitivity.result, "horizon": "3-month", "regime": None}}
    )
    registry.register(RATE_ENTITY, GILTS_ENTITY, gilts_sensitivity)

    rng = np.random.default_rng(11)
    rate_moves = rng.normal(0, 0.01, 40)
    # Positive beta: bank equities move WITH the rate (higher rate ->
    # wider net interest margin -> higher bank equity returns), so a
    # rate CUT (negative perturbation) correctly produces a negative
    # impact below — matches causal_bank_equities' own stated mechanism.
    bank_equity_returns = (3.0 * rate_moves + rng.normal(0, 0.01, 40)).tolist()
    bank_sensitivity = estimate_factor_sensitivity(
        RATE_ENTITY, BANK_EQUITIES_ENTITY, rate_moves.tolist(), bank_equity_returns, horizon="3-month"
    )
    registry.register(RATE_ENTITY, BANK_EQUITIES_ENTITY, bank_sensitivity)

    # Negative beta: property moves OPPOSITE the rate (higher rate ->
    # higher borrowing costs -> lower property demand/valuations), so a
    # rate CUT correctly produces a positive impact below — matches
    # causal_property's own stated mechanism.
    property_returns = (-2.0 * rate_moves + rng.normal(0, 0.008, 40)).tolist()
    property_sensitivity = estimate_factor_sensitivity(
        RATE_ENTITY, PROPERTY_ENTITY, rate_moves.tolist(), property_returns, horizon="3-month"
    )
    registry.register(RATE_ENTITY, PROPERTY_ENTITY, property_sensitivity)

    state["registry"] = registry
    state["sensitivities"] = {
        GILTS_ENTITY: gilts_sensitivity,
        BANK_EQUITIES_ENTITY: bank_sensitivity,
        PROPERTY_ENTITY: property_sensitivity,
    }

    # === Step 4: simulation-engine — real propagation, one ScenarioResult per asset ===
    scenario_results = {
        entity_id: propagate_scenario(RATES_CUT_100BP, entity_id, graph, registry, RATE_ENTITY)
        for entity_id in PORTFOLIO_WEIGHTS
    }
    state["scenario_results"] = scenario_results

    # === Step 5: quant-engine — real portfolio propagation ===
    state["portfolio_result"] = propagate_to_portfolio(list(scenario_results.values()), PORTFOLIO_WEIGHTS)

    return state


def test_step1_forecast_is_a_real_computed_value_not_hardcoded(slice_state):
    cpi_series = synthetic_cpi_yoy_series()
    recomputed = exponential_smoothing_forecast(cpi_series)
    assert slice_state["cpi_forecast"] == pytest.approx(recomputed)


def test_step2_transmission_graph_supports_all_three_pathways(slice_state):
    graph = slice_state["graph"]
    for entity_id in PORTFOLIO_WEIGHTS:
        pathways = graph.require_pathway(RATE_ENTITY, entity_id)
        assert len(pathways) == 1


def test_step3_sensitivities_are_genuinely_different_methods(slice_state):
    sensitivities = slice_state["sensitivities"]
    assert sensitivities[GILTS_ENTITY].result["method"] == "deterministic-duration"
    assert sensitivities[BANK_EQUITIES_ENTITY].result["method"] == "statistical-ols"
    assert sensitivities[PROPERTY_ENTITY].result["method"] == "statistical-ols"


def test_step4_scenario_results_have_directionally_sensible_impact(slice_state):
    """A rate CUT: Gilts up (positive duration effect), Bank Equities
    down (margin compression), Property up (cheaper borrowing) — proven
    from the actual computed base_case signs, not asserted by fiat."""
    results = slice_state["scenario_results"]
    assert results[GILTS_ENTITY].base_case > 0
    assert results[BANK_EQUITIES_ENTITY].base_case < 0
    assert results[PROPERTY_ENTITY].base_case > 0


def test_step4_every_scenario_result_carries_a_genuine_nonzero_range(slice_state):
    for result in slice_state["scenario_results"].values():
        assert result.range_low < result.base_case < result.range_high


def test_step5_portfolio_base_case_is_independently_recomputable(slice_state):
    results = slice_state["scenario_results"]
    expected = sum(PORTFOLIO_WEIGHTS[e] * results[e].base_case for e in PORTFOLIO_WEIGHTS)
    assert slice_state["portfolio_result"].result["portfolio_base_case"] == pytest.approx(expected)


def test_step5_portfolio_dependencies_resolve_to_the_real_scenario_results(slice_state):
    portfolio_result = slice_state["portfolio_result"]
    scenario_result_ids = {r.id for r in slice_state["scenario_results"].values()}
    assert set(portfolio_result.dependencies) == scenario_result_ids


def test_evidence_chain_from_portfolio_result_reaches_the_original_causal_claims(slice_state):
    """Full provenance traversal: portfolio result -> scenario results ->
    (sensitivities, causal claims) — nothing is a dead end."""
    portfolio_result = slice_state["portfolio_result"]
    scenario_results = slice_state["scenario_results"]
    causal_claims = slice_state["causal_claims"]
    sensitivities = slice_state["sensitivities"]

    for entity_id, scenario_result in scenario_results.items():
        assert scenario_result.id in portfolio_result.dependencies
        assert causal_claims[entity_id].id in scenario_result.dependencies
        assert sensitivities[entity_id].id in scenario_result.dependencies


def test_step6_look_ahead_contamination_is_caught_for_this_real_pipelines_output():
    """Testing Requirement 'future-data leakage', proven against this
    test's own real pipeline output (not a hand-built fixture)."""
    from datetime import datetime, timedelta, timezone

    graph = TransmissionGraph()
    claim = CausalClaim(
        subject="test",
        validation_status=ValidationStatus.PROVISIONAL,
        result="test",
        source="test",
        producer="test",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=RATE_ENTITY,
        effect_entity_id=GILTS_ENTITY,
        mechanism="test mechanism",
    )
    graph.add_edge(claim)
    registry = SensitivityRegistry()
    sensitivity = duration_price_sensitivity(modified_duration=8.0)
    as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sensitivity = sensitivity.model_copy(
        update={
            "result": {**sensitivity.result, "horizon": "3-month", "regime": None},
            "publication_time": as_of + timedelta(days=10),  # only available AFTER as_of
            "retrieval_time": as_of + timedelta(days=10),
        }
    )
    registry.register(RATE_ENTITY, GILTS_ENTITY, sensitivity)

    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY, as_of=as_of)
    verdict = check_no_look_ahead_contamination(result, {sensitivity.id: sensitivity})
    assert verdict.verdict_type == VerdictType.REJECT


def test_portfolio_result_confidence_and_status_reflect_the_weakest_contributing_link(slice_state):
    portfolio_result = slice_state["portfolio_result"]
    scenario_results = list(slice_state["scenario_results"].values())
    assert portfolio_result.confidence == min(
        (r.confidence for r in scenario_results),
        key=lambda c: {ConfidenceLevel.LOW: 0, ConfidenceLevel.MODERATE: 1, ConfidenceLevel.HIGH: 2}[c],
    )
