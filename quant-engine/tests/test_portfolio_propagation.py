"""
Tests for propagate_to_portfolio — PHASE E4 Part 7.

Uses a lightweight, LOCAL stand-in for a `ScenarioResult` (a plain
dataclass with the same field names) rather than importing
`optifi_simulation` — `simulation-engine` already depends on
`quant-engine` at runtime (Part 3's sensitivity tools), so quant-engine
deliberately does not depend back on simulation-engine, even for tests,
to avoid a circular package dependency. `propagate_to_portfolio` itself
is duck-typed against exactly this shape (see its own module docstring)
— genuine `ScenarioResult` objects are exercised directly in
simulation-engine's own test suite and in the cross-package integration
test.
"""

from dataclasses import dataclass, field
from uuid import uuid4

import pytest
from optifi_shared import ConfidenceLevel, UnsupportedFailure, ValidationStatus

from optifi_quant import propagate_to_portfolio


@dataclass
class _ScenarioResultStub:
    affected_entity_id: str
    base_case: float
    range_low: float
    range_high: float
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    validation_status: ValidationStatus = ValidationStatus.PROVISIONAL
    id: str = field(default_factory=lambda: str(uuid4()))


def _sr(entity_id: str, base_case: float, range_low: float, range_high: float, **overrides) -> _ScenarioResultStub:
    return _ScenarioResultStub(entity_id, base_case, range_low, range_high, **overrides)


# --- correctness ---


def test_portfolio_base_case_is_the_weighted_sum():
    scenario_results = [
        _sr("entity:a", 0.10, 0.05, 0.15),
        _sr("entity:b", -0.04, -0.08, 0.0),
    ]
    holdings = {"entity:a": 0.6, "entity:b": 0.4}
    result = propagate_to_portfolio(scenario_results, holdings)
    expected = 0.6 * 0.10 + 0.4 * -0.04
    assert result.result["portfolio_base_case"] == pytest.approx(expected)


def test_portfolio_range_is_the_weighted_sum_of_bounds():
    scenario_results = [
        _sr("entity:a", 0.10, 0.05, 0.15),
        _sr("entity:b", -0.04, -0.08, 0.0),
    ]
    holdings = {"entity:a": 0.6, "entity:b": 0.4}
    result = propagate_to_portfolio(scenario_results, holdings)
    assert result.result["range_low"] == pytest.approx(0.6 * 0.05 + 0.4 * -0.08)
    assert result.result["range_high"] == pytest.approx(0.6 * 0.15 + 0.4 * 0.0)


def test_contributions_show_per_holding_attribution():
    """Part 7: 'The final output must clearly identify which
    assumptions drove the portfolio result.'"""
    scenario_results = [
        _sr("entity:a", 0.10, 0.05, 0.15),
        _sr("entity:b", -0.04, -0.08, 0.0),
    ]
    holdings = {"entity:a": 0.6, "entity:b": 0.4}
    result = propagate_to_portfolio(scenario_results, holdings)
    contributions = result.result["contributions"]
    assert contributions["entity:a"]["weighted_contribution"] == pytest.approx(0.06)
    assert contributions["entity:b"]["weighted_contribution"] == pytest.approx(-0.016)
    # sorted by contribution magnitude, largest first
    assert list(contributions.keys())[0] == "entity:a"


def test_dependencies_reference_every_contributing_scenario_result():
    scenario_results = [_sr("entity:a", 0.1, 0.05, 0.15), _sr("entity:b", -0.04, -0.08, 0.0)]
    holdings = {"entity:a": 0.6, "entity:b": 0.4}
    result = propagate_to_portfolio(scenario_results, holdings)
    assert set(result.dependencies) == {sr.id for sr in scenario_results}


def test_confidence_reflects_the_worst_contributing_confidence():
    scenario_results = [
        _sr("entity:a", 0.1, 0.05, 0.15, confidence=ConfidenceLevel.MODERATE),
        _sr("entity:b", -0.04, -0.08, 0.0, confidence=ConfidenceLevel.LOW),
    ]
    holdings = {"entity:a": 0.6, "entity:b": 0.4}
    result = propagate_to_portfolio(scenario_results, holdings)
    assert result.confidence == ConfidenceLevel.LOW


def test_validation_status_reflects_the_worst_contributing_status():
    scenario_results = [
        _sr("entity:a", 0.1, 0.05, 0.15, validation_status=ValidationStatus.CONFLICTED),
        _sr("entity:b", -0.04, -0.08, 0.0, validation_status=ValidationStatus.PROVISIONAL),
    ]
    holdings = {"entity:a": 0.6, "entity:b": 0.4}
    result = propagate_to_portfolio(scenario_results, holdings)
    assert result.validation_status == ValidationStatus.CONFLICTED


# --- Testing Requirement: "unsupported asset" ---


def test_holding_with_no_matching_scenario_result_raises():
    scenario_results = [_sr("entity:a", 0.1, 0.05, 0.15)]
    holdings = {"entity:a": 0.5, "entity:unsupported": 0.5}
    with pytest.raises(UnsupportedFailure):
        propagate_to_portfolio(scenario_results, holdings)


# --- structural guards ---


def test_weights_not_summing_to_one_raises():
    scenario_results = [_sr("entity:a", 0.1, 0.05, 0.15)]
    with pytest.raises(ValueError):
        propagate_to_portfolio(scenario_results, {"entity:a": 0.5})


def test_empty_holdings_raises():
    with pytest.raises(ValueError):
        propagate_to_portfolio([], {})


def test_malformed_scenario_result_missing_required_attribute_raises_type_error():
    class _NotAScenarioResult:
        pass

    with pytest.raises(TypeError):
        propagate_to_portfolio([_NotAScenarioResult()], {"entity:a": 1.0})


def test_single_holding_full_weight():
    scenario_results = [_sr("entity:a", 0.1, 0.05, 0.15)]
    result = propagate_to_portfolio(scenario_results, {"entity:a": 1.0})
    assert result.result["portfolio_base_case"] == pytest.approx(0.1)
