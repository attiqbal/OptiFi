"""
Tests for extract_structured_claim (Stage 3 support, AI_ENGINE_SPEC.md
Section 3.1; Never-list item 8: never self-certify extraction as
VERIFIED).
"""

import inspect

import pytest
from optifi_shared import InformationClass, ValidationStatus

from optifi_ai import StubExplanationGenerator, extract_structured_claim


def test_extraction_is_always_fact_and_provisional():
    claim = extract_structured_claim(
        "The company reported Q2 revenue of $4.2bn.", StubExplanationGenerator()
    )
    assert claim.information_class == InformationClass.FACT
    assert claim.validation_status == ValidationStatus.PROVISIONAL


def test_extraction_is_provisional_regardless_of_input_text_content():
    """
    Even text that itself claims certainty ("this is confirmed and
    verified") must not influence the hard-coded validation_status.
    """
    claim = extract_structured_claim(
        "This is a confirmed, fully verified, 100% certain fact.",
        StubExplanationGenerator(),
    )
    assert claim.validation_status == ValidationStatus.PROVISIONAL


def test_function_signature_has_no_validation_status_parameter():
    """
    The strongest proof that nothing can override PROVISIONAL: there is no
    parameter through which a caller could even attempt to pass one.
    """
    signature = inspect.signature(extract_structured_claim)
    assert "validation_status" not in signature.parameters


def test_passing_a_validation_status_keyword_raises_type_error():
    with pytest.raises(TypeError):
        extract_structured_claim(
            "some text",
            StubExplanationGenerator(),
            validation_status=ValidationStatus.VERIFIED,  # type: ignore[call-arg]
        )
