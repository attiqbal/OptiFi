"""
Tests for the illustrative rate-cut CausalClaim example.
"""

from optifi_shared import ConfidenceLevel, InformationClass, ValidationStatus

from optifi_causal.examples import example_rate_cut_mortgage_claim


def test_example_rate_cut_mortgage_claim_is_correctly_shaped():
    claim = example_rate_cut_mortgage_claim()

    assert claim.information_class == InformationClass.ESTIMATE
    assert claim.validation_status == ValidationStatus.PROVISIONAL
    assert claim.cause_entity_id
    assert claim.effect_entity_id
    assert claim.mechanism
    assert claim.confidence == ConfidenceLevel.LOW
    assert claim.limitations
