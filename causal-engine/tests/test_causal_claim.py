"""
Tests for CausalClaim (CAUSAL_ENGINE_SPEC.md, Section 5) — in particular
the correlation-causation guardrail (Section 5.2 / Section 6).
"""

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, ValidationStatus
from pydantic import ValidationError

from optifi_causal import CausalClaim


def _base_kwargs() -> dict:
    """Valid CausalClaim data, minus mechanism/historical_precedent."""
    return dict(
        subject="illustrative cause -> effect claim",
        validation_status=ValidationStatus.PROVISIONAL,
        result="illustrative claim result",
        source="illustrative test source",
        producer="causal-engine (test)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id="entity:cause",
        effect_entity_id="entity:effect",
    )


def test_mechanism_only_is_valid():
    claim = CausalClaim(
        **_base_kwargs(),
        mechanism="a plausible economic mechanism connecting cause to effect",
    )
    assert claim.mechanism is not None
    assert claim.historical_precedent is None


def test_historical_precedent_only_is_valid():
    claim = CausalClaim(
        **_base_kwargs(),
        historical_precedent="this relationship has held across three prior cycles",
    )
    assert claim.historical_precedent is not None
    assert claim.mechanism is None


def test_both_mechanism_and_precedent_is_valid():
    claim = CausalClaim(
        **_base_kwargs(),
        mechanism="a plausible economic mechanism",
        historical_precedent="held across three prior cycles",
    )
    assert claim.mechanism is not None
    assert claim.historical_precedent is not None


def test_neither_mechanism_nor_precedent_raises_error():
    """
    The single most important test in this module: a CausalClaim with
    neither a stated mechanism nor historical precedent is bare
    correlation, and CAUSAL_ENGINE_SPEC.md Section 5.2/6 says that must
    never be output as a causal claim. This must fail construction.
    """
    with pytest.raises(ValidationError):
        CausalClaim(**_base_kwargs())


def test_neither_mechanism_nor_precedent_raises_error_when_blank_strings():
    """Whitespace-only values don't count as 'present' either."""
    with pytest.raises(ValidationError):
        CausalClaim(**_base_kwargs(), mechanism="   ", historical_precedent="")


def test_information_class_defaults_to_estimate():
    claim = CausalClaim(**_base_kwargs(), mechanism="a mechanism")
    assert claim.information_class == InformationClass.ESTIMATE


@pytest.mark.parametrize(
    "other_class",
    [InformationClass.FACT, InformationClass.JUDGEMENT],
)
def test_information_class_cannot_be_set_to_anything_other_than_estimate(other_class):
    with pytest.raises(ValidationError):
        CausalClaim(
            **_base_kwargs(),
            mechanism="a mechanism",
            information_class=other_class,
        )


# --- Phase E4: regime field (purely additive) ---


def test_regime_defaults_to_none():
    claim = CausalClaim(**_base_kwargs(), mechanism="a mechanism")
    assert claim.regime is None


def test_regime_can_be_set_to_free_text():
    claim = CausalClaim(**_base_kwargs(), mechanism="a mechanism", regime="high-inflation")
    assert claim.regime == "high-inflation"


def test_existing_construction_pattern_unaffected_by_new_regime_field():
    """The guardrail from before Phase E4 still fires exactly as it did —
    adding `regime` did not loosen or otherwise touch it."""
    with pytest.raises(ValidationError):
        CausalClaim(**_base_kwargs(), regime="high-inflation")  # no mechanism/precedent
