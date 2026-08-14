"""
Tests for propagate_scenario — PHASE E4 Parts 1-5, and the Testing
Requirements: "unsupported asset," "missing factor exposure,"
"wrong-horizon sensitivity," "regime mismatch," "conflicting
asset-response models," "deterministic single-number simulation,"
"future-data leakage."
"""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from optifi_causal import CausalClaim, TransmissionGraph
from optifi_quant import duration_price_sensitivity, estimate_factor_sensitivity, SensitivityRegistry
from optifi_shared import (
    ConfidenceLevel,
    ConflictedInputFailure,
    InformationClass,
    MissingInputFailure,
    OutOfDistributionFailure,
    UnsupportedFailure,
    UAP,
    ValidationStatus,
)
from optifi_verification import check_no_look_ahead_contamination, VerdictType

from optifi_simulation import propagate_scenario
from optifi_simulation.scenario_library import RATES_CUT_100BP, ScenarioDefinition

RATE_ENTITY = "entity:uk-base-rate"
GILTS_ENTITY = "entity:uk-gilts"


def _rate_to_gilts_claim() -> CausalClaim:
    return CausalClaim(
        subject="UK base rate -> UK Gilts",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A base rate cut is associated with higher Gilt prices",
        source="test",
        producer="causal-engine (test)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=RATE_ENTITY,
        effect_entity_id=GILTS_ENTITY,
        mechanism="Lower base rate reduces yields; existing higher-coupon Gilts become relatively more attractive.",
    )


def _graph_with_gilts_pathway() -> TransmissionGraph:
    graph = TransmissionGraph()
    graph.add_edge(_rate_to_gilts_claim())
    return graph


def _registry_with_duration_sensitivity(regime: str | None = None) -> SensitivityRegistry:
    registry = SensitivityRegistry()
    uap = duration_price_sensitivity(modified_duration=7.0)
    uap = uap.model_copy(update={"result": {**uap.result, "horizon": "3-month", "regime": regime}})
    registry.register(RATE_ENTITY, GILTS_ENTITY, uap)
    return registry


# --- basic correctness ---


def test_propagate_scenario_produces_a_real_computed_result():
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity()

    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)

    # -100bp = -0.01 decimal; duration sensitivity = -7.0;
    # base_case = -7.0 * -0.01 = 0.07 (a 7% price increase).
    assert result.base_case == pytest.approx(0.07)
    assert result.range_low < result.base_case < result.range_high
    assert result.affected_entity_id == GILTS_ENTITY


def test_propagated_range_has_genuine_nonzero_width():
    """Testing Requirement: 'deterministic single-number simulation' —
    propagate_scenario's own output must never collapse to a point."""
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity()
    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)
    assert result.range_high > result.range_low


def test_dependencies_reference_both_the_causal_edge_and_the_sensitivity():
    graph = _graph_with_gilts_pathway()
    claim = graph.edges_from(RATE_ENTITY)[0]
    registry = _registry_with_duration_sensitivity()
    sensitivity_uap = registry.get_sensitivity(RATE_ENTITY, GILTS_ENTITY).single()

    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)

    assert claim.id in result.dependencies
    assert sensitivity_uap.id in result.dependencies


def test_statistical_sensitivity_produces_a_computed_confidence_interval_range():
    graph = _graph_with_gilts_pathway()
    rng = np.random.default_rng(3)
    factor = rng.normal(0, 0.01, 50).tolist()
    asset = (1.5 * np.array(factor) + rng.normal(0, 0.002, 50)).tolist()
    sensitivity_uap = estimate_factor_sensitivity(RATE_ENTITY, GILTS_ENTITY, factor, asset, horizon="3-month")
    registry = SensitivityRegistry()
    registry.register(RATE_ENTITY, GILTS_ENTITY, sensitivity_uap)

    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)
    # base_case should be in the direction implied by the positive beta and negative perturbation.
    assert result.base_case < 0  # beta positive (~1.5), perturbation negative (-1%) => negative impact
    assert result.range_low < result.range_high


# --- Testing Requirement: "unsupported asset" ---


def test_unsupported_asset_raises_when_no_causal_pathway_exists():
    graph = TransmissionGraph()  # empty — no pathway registered at all
    registry = _registry_with_duration_sensitivity()
    with pytest.raises(UnsupportedFailure):
        propagate_scenario(RATES_CUT_100BP, "entity:completely-unrelated-asset", graph, registry, RATE_ENTITY)


# --- Testing Requirement: "missing factor exposure" ---


def test_missing_factor_exposure_raises_when_pathway_exists_but_no_sensitivity():
    graph = _graph_with_gilts_pathway()  # pathway exists
    registry = SensitivityRegistry()  # but nothing quantifies it
    with pytest.raises(MissingInputFailure):
        propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)


# --- Testing Requirement: "wrong-horizon sensitivity" ---


def test_wrong_horizon_sensitivity_raises():
    graph = _graph_with_gilts_pathway()
    registry = SensitivityRegistry()
    uap = duration_price_sensitivity(modified_duration=7.0)
    # sensitivity estimated at a 1-month horizon; scenario is 3-month.
    uap = uap.model_copy(update={"result": {**uap.result, "horizon": "1-month", "regime": None}})
    registry.register(RATE_ENTITY, GILTS_ENTITY, uap)

    with pytest.raises(UnsupportedFailure):
        propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)


def test_matching_horizon_does_not_raise():
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity()  # already horizon="3-month", matches RATES_CUT_100BP
    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)
    assert result is not None


# --- Testing Requirement: "regime mismatch" ---


def test_regime_mismatch_falls_back_and_flags_low_confidence():
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity(regime=None)  # regime-agnostic only

    result = propagate_scenario(
        RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY, regime="crisis"
    )
    assert result.confidence == ConfidenceLevel.LOW
    assert any("regime" in note.lower() for note in result.limitations)


def test_regime_mismatch_with_no_fallback_available_propagates_the_registry_failure():
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity(regime="low-inflation")  # only low-inflation registered
    with pytest.raises(OutOfDistributionFailure):
        propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY, regime="crisis")


# --- Testing Requirement: "conflicting asset-response models" ---


def test_conflicting_asset_response_models_raise_via_single():
    graph = _graph_with_gilts_pathway()
    registry = SensitivityRegistry()
    uap_a = duration_price_sensitivity(modified_duration=5.0)
    uap_a = uap_a.model_copy(update={"result": {**uap_a.result, "horizon": "3-month", "regime": None}})
    uap_b = duration_price_sensitivity(modified_duration=9.0)
    uap_b = uap_b.model_copy(update={"result": {**uap_b.result, "horizon": "3-month", "regime": None}})
    registry.register(RATE_ENTITY, GILTS_ENTITY, uap_a)
    registry.register(RATE_ENTITY, GILTS_ENTITY, uap_b)

    with pytest.raises(ConflictedInputFailure):
        propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY)


# --- Testing Requirement: "future-data leakage" ---


def test_future_data_leakage_is_caught_by_the_existing_look_ahead_check():
    """propagate_scenario correctly wires as_of/dependencies so
    verification-engine's existing check_no_look_ahead_contamination
    can independently catch a scenario result depending on a causal
    claim or sensitivity that wasn't genuinely available yet."""
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity()
    sensitivity_uap = registry.get_sensitivity(RATE_ENTITY, GILTS_ENTITY).single()

    as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY, as_of=as_of)

    # Simulate the sensitivity actually only having become available
    # AFTER the scenario's as_of cutoff.
    leaked_sensitivity = sensitivity_uap.model_copy(
        update={"publication_time": as_of + timedelta(days=30), "retrieval_time": as_of + timedelta(days=30)}
    )
    known_packets = {leaked_sensitivity.id: leaked_sensitivity}
    verdict = check_no_look_ahead_contamination(result, known_packets)
    assert verdict.verdict_type == VerdictType.REJECT


def test_no_leakage_when_dependencies_genuinely_predate_as_of():
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity()
    sensitivity_uap = registry.get_sensitivity(RATE_ENTITY, GILTS_ENTITY).single()

    as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = propagate_scenario(RATES_CUT_100BP, GILTS_ENTITY, graph, registry, RATE_ENTITY, as_of=as_of)

    genuinely_available = sensitivity_uap.model_copy(
        update={
            "publication_time": as_of - timedelta(days=30),
            "retrieval_time": as_of - timedelta(days=30),
        }
    )
    causal_edge = graph.edges_from(RATE_ENTITY)[0].model_copy(
        update={
            "publication_time": as_of - timedelta(days=60),
            "retrieval_time": as_of - timedelta(days=60),
        }
    )
    known_packets = {genuinely_available.id: genuinely_available, causal_edge.id: causal_edge}
    verdict = check_no_look_ahead_contamination(result, known_packets)
    assert verdict.verdict_type == VerdictType.PASS


# --- unrecognised unit ---


def test_unrecognised_scenario_unit_raises_unsupported():
    graph = _graph_with_gilts_pathway()
    registry = _registry_with_duration_sensitivity()
    bad_scenario = ScenarioDefinition(
        scenario_id="bad_unit_scenario",
        family="rates",
        description="bad unit test",
        perturbed_entity_id=RATE_ENTITY,
        perturbation_magnitude=1.0,
        unit="sigma",  # not a recognised unit
        horizon="3-month",
        justification="test only",
    )
    with pytest.raises(UnsupportedFailure):
        propagate_scenario(bad_scenario, GILTS_ENTITY, graph, registry, RATE_ENTITY)
