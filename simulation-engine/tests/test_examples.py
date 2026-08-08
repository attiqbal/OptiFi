"""
Tests for the illustrative rate-cut Gilt-impact ScenarioResult example.
"""

from optifi_shared import ConfidenceLevel, InformationClass, ValidationStatus

from optifi_simulation.examples import example_rate_cut_gilt_impact


def test_example_rate_cut_gilt_impact_is_correctly_shaped():
    result = example_rate_cut_gilt_impact()

    assert result.information_class == InformationClass.ESTIMATE
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.scenario_description
    assert result.affected_entity_id
    assert result.range_low <= result.base_case <= result.range_high
    assert result.confidence == ConfidenceLevel.LOW
    assert result.sensitivity_factors
    assert result.limitations
