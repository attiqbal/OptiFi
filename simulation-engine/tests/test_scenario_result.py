"""
Tests for ScenarioResult (SIMULATION_ENGINE_SPEC.md, Sections 7/8) — in
particular the mandatory-range guardrail (Section 8).
"""

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, ValidationStatus
from pydantic import ValidationError

from optifi_simulation import ScenarioResult


def _base_kwargs() -> dict:
    """Valid ScenarioResult data, minus range_low/range_high/sensitivity_factors."""
    return dict(
        subject="illustrative scenario",
        validation_status=ValidationStatus.PROVISIONAL,
        result="illustrative scenario result",
        source="illustrative test source",
        producer="simulation-engine (test)",
        confidence=ConfidenceLevel.LOW,
        scenario_description="illustrative perturbation: -100bp",
        affected_entity_id="entity:illustrative-asset-class",
        base_case=0.02,
    )


def test_valid_scenario_result_with_base_case_and_range():
    result = ScenarioResult(
        **_base_kwargs(),
        range_low=-0.01,
        range_high=0.05,
        sensitivity_factors=["illustrative factor"],
    )
    assert result.base_case == 0.02
    assert result.range_low == -0.01
    assert result.range_high == 0.05


def test_missing_range_low_raises_error():
    """
    The single most important test in this module, mirroring
    CausalClaim's primary guardrail test: a ScenarioResult with only
    base_case and no range must never be constructible
    (SIMULATION_ENGINE_SPEC.md Section 8).
    """
    with pytest.raises(ValidationError):
        ScenarioResult(
            **_base_kwargs(),
            range_high=0.05,
            sensitivity_factors=[],
        )


def test_missing_range_high_raises_error():
    with pytest.raises(ValidationError):
        ScenarioResult(
            **_base_kwargs(),
            range_low=-0.01,
            sensitivity_factors=[],
        )


def test_missing_both_range_bounds_raises_error():
    with pytest.raises(ValidationError):
        ScenarioResult(**_base_kwargs(), sensitivity_factors=[])


def test_range_not_containing_base_case_raises_error():
    # base_case=0.02, but the range [0.05, 0.10] doesn't contain it.
    with pytest.raises(ValidationError):
        ScenarioResult(
            **_base_kwargs(),
            range_low=0.05,
            range_high=0.10,
            sensitivity_factors=[],
        )


def test_information_class_defaults_to_estimate():
    result = ScenarioResult(
        **_base_kwargs(), range_low=-0.01, range_high=0.05, sensitivity_factors=[]
    )
    assert result.information_class == InformationClass.ESTIMATE


@pytest.mark.parametrize(
    "other_class",
    [InformationClass.FACT, InformationClass.JUDGEMENT],
)
def test_information_class_cannot_be_set_to_anything_other_than_estimate(other_class):
    with pytest.raises(ValidationError):
        ScenarioResult(
            **_base_kwargs(),
            range_low=-0.01,
            range_high=0.05,
            sensitivity_factors=[],
            information_class=other_class,
        )


def test_sensitivity_factors_must_be_explicitly_provided():
    with pytest.raises(ValidationError):
        ScenarioResult(**_base_kwargs(), range_low=-0.01, range_high=0.05)


def test_sensitivity_factors_empty_list_is_accepted():
    result = ScenarioResult(
        **_base_kwargs(), range_low=-0.01, range_high=0.05, sensitivity_factors=[]
    )
    assert result.sensitivity_factors == []
