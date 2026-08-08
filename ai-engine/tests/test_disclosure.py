"""
Tests for explain_with_disclosure (Stage 13, AI_ENGINE_SPEC.md Section
3.4; Never-list item 9: never present a non-VERIFIED item without
flagging its validation_status).
"""

from typing import Any

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_ai import StubExplanationGenerator, explain_with_disclosure


class SilentOnStatusGenerator:
    """A cooperative generator whose text never mentions validation status
    at all — proves the disclosure comes from code, not the generator."""

    def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "Here is a clean summary of your portfolio's recent performance."


def _make_uap(subject: str, validation_status: ValidationStatus) -> UAP:
    return UAP(
        subject=subject,
        information_class=InformationClass.ESTIMATE,
        validation_status=validation_status,
        result="some result",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_disclosure_appears_even_when_generator_says_nothing_about_status():
    provisional = _make_uap("forecast A", ValidationStatus.PROVISIONAL)

    explanation = explain_with_disclosure([provisional], SilentOnStatusGenerator())

    assert "validation_status=PROVISIONAL" in "".join(explanation.limitations)
    assert "PROVISIONAL" in explanation.result


def test_verified_items_get_no_disclosure_note():
    verified = _make_uap("fact A", ValidationStatus.VERIFIED)
    explanation = explain_with_disclosure([verified], StubExplanationGenerator())
    assert explanation.limitations == []


def test_mixed_inputs_only_disclose_non_verified_ones():
    verified = _make_uap("fact A", ValidationStatus.VERIFIED)
    conflicted = _make_uap("estimate B", ValidationStatus.CONFLICTED)
    stale = _make_uap("estimate C", ValidationStatus.STALE)

    explanation = explain_with_disclosure(
        [verified, conflicted, stale], StubExplanationGenerator()
    )

    assert len(explanation.limitations) == 2
    joined = "".join(explanation.limitations)
    assert "fact A" not in joined
    assert "estimate B" in joined and "CONFLICTED" in joined
    assert "estimate C" in joined and "STALE" in joined


def test_all_input_ids_appear_in_dependencies():
    verified = _make_uap("fact A", ValidationStatus.VERIFIED)
    provisional = _make_uap("estimate B", ValidationStatus.PROVISIONAL)

    explanation = explain_with_disclosure([verified, provisional], StubExplanationGenerator())

    assert verified.id in explanation.dependencies
    assert provisional.id in explanation.dependencies
