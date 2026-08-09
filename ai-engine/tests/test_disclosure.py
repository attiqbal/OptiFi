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


# --- Recursive disclosure via known_uaps (the Attack 3 fix), and the
# --- never-silently-incomplete fix layered on top of it ---


def _make_uap_with_deps(
    subject: str, validation_status: ValidationStatus, dependencies: list[str]
) -> UAP:
    return UAP(
        subject=subject,
        information_class=InformationClass.ESTIMATE,
        validation_status=validation_status,
        result="some result",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=dependencies,
    )


def test_unresolved_dependency_produces_an_incompleteness_note_not_silence():
    """
    The gap this task closes: previously, omitting known_uaps meant a
    top-level UAP's own unresolved dependencies were silently ignored —
    a VERIFIED-looking judgement with a genuinely unresolvable
    PROVISIONAL ancestor produced an empty, clean-looking disclosure.
    Now it must say it couldn't check.
    """
    buried = _make_uap("buried fact", ValidationStatus.PROVISIONAL)
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, [buried.id])

    explanation = explain_with_disclosure([top], StubExplanationGenerator())

    assert explanation.limitations != []
    joined = " ".join(explanation.limitations)
    assert "top judgement" in joined
    assert "could not be resolved" in joined
    assert buried.id in joined


def test_true_leaf_uap_produces_no_spurious_incompleteness_note():
    """
    A UAP with no dependencies/provenance_chain at all has nothing
    unresolved — confirms the fix doesn't over-trigger.
    """
    leaf = _make_uap("standalone fact", ValidationStatus.VERIFIED)
    explanation = explain_with_disclosure([leaf], StubExplanationGenerator())
    assert explanation.limitations == []


def test_uaps_referencing_each_other_directly_need_no_known_uaps():
    """
    A reference that points at another UAP already in the top-level
    `uaps` list is resolved from that list itself — a caller who passes
    a complete, self-contained set doesn't need known_uaps just to
    cross-reference within it.
    """
    buried = _make_uap("buried fact", ValidationStatus.PROVISIONAL)
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, [buried.id])

    explanation = explain_with_disclosure([buried, top], StubExplanationGenerator())

    joined = " ".join(explanation.limitations)
    assert "buried fact" in joined and "PROVISIONAL" in joined
    assert "could not be resolved" not in joined


def test_known_uaps_walks_multiple_hops_and_discloses_buried_provisional():
    buried_fact = _make_uap("buried fact", ValidationStatus.PROVISIONAL)
    middle = _make_uap_with_deps("middle estimate", ValidationStatus.VERIFIED, [buried_fact.id])
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, [middle.id])

    known_uaps = {u.id: u for u in [buried_fact, middle, top]}
    explanation = explain_with_disclosure([top], StubExplanationGenerator(), known_uaps=known_uaps)

    joined = " ".join(explanation.limitations)
    assert "buried fact" in joined
    assert "PROVISIONAL" in joined


def test_unresolved_reference_is_flagged_not_silently_skipped():
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, ["nonexistent-id"])

    explanation = explain_with_disclosure([top], StubExplanationGenerator(), known_uaps={})

    joined = " ".join(explanation.limitations)
    assert "nonexistent-id" in joined
    assert "could not be resolved" in joined


def test_partial_known_uaps_names_specifically_which_reference_is_unresolved():
    """
    known_uaps resolves one of two dependencies but not the other — the
    note must name only the genuinely unresolved one, not a generic
    catch-all covering both.
    """
    resolvable = _make_uap("resolvable ancestor", ValidationStatus.VERIFIED)
    top = _make_uap_with_deps(
        "top judgement", ValidationStatus.VERIFIED, [resolvable.id, "still-missing-id"]
    )

    explanation = explain_with_disclosure(
        [top], StubExplanationGenerator(), known_uaps={resolvable.id: resolvable}
    )

    joined = " ".join(explanation.limitations)
    assert "still-missing-id" in joined
    assert resolvable.id not in joined  # the resolved one is not named as unresolved
    assert "could not be resolved" in joined
