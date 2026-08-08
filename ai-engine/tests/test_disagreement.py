"""
Tests for disagreement grouping and preservation (Stage 12,
AI_ENGINE_SPEC.md Section 3.3; Never-list item 3: never mathematically
resolve multi-model disagreement).
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_ai import (
    DISAGREEMENT_TOLERANCE,
    StubExplanationGenerator,
    group_by_disagreement_set,
    has_genuine_disagreement,
    synthesize_with_disagreement_preserved,
)


def _make_forecast(result: float, disagreement_set_ref: str | None) -> UAP:
    return UAP(
        subject="recession probability forecast",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.VERIFIED,
        result=result,
        source="forecast-engine",
        producer="forecast-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
        disagreement_set_ref=disagreement_set_ref,
    )


# --- group_by_disagreement_set ---


def test_groups_by_disagreement_set_ref():
    a = _make_forecast(0.10, "set-1")
    b = _make_forecast(0.30, "set-1")
    c = _make_forecast(0.05, "set-2")
    ungrouped = _make_forecast(0.20, None)

    groups = group_by_disagreement_set([a, b, c, ungrouped])

    assert set(groups.keys()) == {"set-1", "set-2"}
    assert groups["set-1"] == [a, b]
    assert groups["set-2"] == [c]


# --- has_genuine_disagreement ---


def test_single_member_group_is_not_genuine_disagreement():
    assert has_genuine_disagreement([_make_forecast(0.10, "set-1")]) is False


def test_numeric_values_within_tolerance_are_not_genuine_disagreement():
    a = _make_forecast(0.100000, "set-1")
    b = _make_forecast(0.100000 + DISAGREEMENT_TOLERANCE / 10, "set-1")
    assert has_genuine_disagreement([a, b]) is False


def test_numeric_values_beyond_tolerance_are_genuine_disagreement():
    a = _make_forecast(0.10, "set-1")
    b = _make_forecast(0.30, "set-1")
    assert has_genuine_disagreement([a, b]) is True


def test_identical_non_numeric_values_are_not_genuine_disagreement():
    a = _make_forecast("recession likely", "set-1")
    b = _make_forecast("recession likely", "set-1")
    assert has_genuine_disagreement([a, b]) is False


def test_differing_non_numeric_values_are_genuine_disagreement():
    a = _make_forecast("recession likely", "set-1")
    b = _make_forecast("soft landing likely", "set-1")
    assert has_genuine_disagreement([a, b]) is True


# --- synthesize_with_disagreement_preserved ---


def test_all_three_disagreeing_members_preserved_in_dependencies():
    a = _make_forecast(0.10, "set-1")
    b = _make_forecast(0.30, "set-1")
    c = _make_forecast(0.55, "set-1")
    groups = group_by_disagreement_set([a, b, c])

    synthesis = synthesize_with_disagreement_preserved(groups, StubExplanationGenerator())

    assert a.id in synthesis.dependencies
    assert b.id in synthesis.dependencies
    assert c.id in synthesis.dependencies
    assert len(synthesis.dependencies) == 3


def test_genuine_disagreement_is_noted_but_not_resolved():
    a = _make_forecast(0.10, "set-1")
    b = _make_forecast(0.55, "set-1")
    groups = group_by_disagreement_set([a, b])

    synthesis = synthesize_with_disagreement_preserved(groups, StubExplanationGenerator())

    assert any("genuine disagreement" in note for note in synthesis.limitations)
    # The synthesis result is narrative text, not a resolved numeric value.
    assert isinstance(synthesis.result, str)


def test_synthesis_is_judgement_and_provisional():
    a = _make_forecast(0.10, "set-1")
    groups = group_by_disagreement_set([a])
    synthesis = synthesize_with_disagreement_preserved(groups, StubExplanationGenerator())
    assert synthesis.information_class == InformationClass.JUDGEMENT
    assert synthesis.validation_status == ValidationStatus.PROVISIONAL
