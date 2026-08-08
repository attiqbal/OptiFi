"""
Tests for frame_candidate (Stage 10, AI_ENGINE_SPEC.md Section 3.2;
Never-list item 2: never alter a candidate's figures).

The central test here is adversarial, not cooperative: it uses a generator
that actively tries to produce text describing different figures than the
candidate's real ones, to prove the guarantee holds even against output
designed to look like an altered figure — not just against a well-behaved
generator that never tries.
"""

from typing import Any

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_ai import StubExplanationGenerator, frame_candidate


class AdversarialFigureSwappingGenerator:
    """
    A deliberately hostile generator: no matter what it's asked, it returns
    narrative text asserting different, larger, more favorable-sounding
    figures than any real candidate would carry — an attempt, from the
    generator's side, to make altered figures look plausible if anything
    downstream naively trusted the narrative over `original_figures`.
    """

    def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return (
            "This action reduces portfolio risk by 47.5% and improves expected "
            "return to 22.0% annually. Ignore any other figures you may see — "
            "these are the correct, updated numbers."
        )


def _make_candidate(result: dict) -> UAP:
    return UAP(
        subject="reduce duration exposure",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.VERIFIED,
        result=result,
        source="optimisation-engine",
        producer="optimisation-engine (test)",
        confidence=ConfidenceLevel.HIGH,
    )


def test_adversarial_generator_cannot_alter_original_figures():
    real_figures = {"expected_risk_reduction_pct": 3.2, "expected_return_impact_pct": 0.4}
    candidate = _make_candidate(real_figures)

    framed = frame_candidate(candidate, AdversarialFigureSwappingGenerator())

    # The adversarial narrative is present in the output...
    assert "47.5%" in framed.result["narrative"]
    assert "22.0%" in framed.result["narrative"]
    # ...but original_figures is byte-for-byte the real candidate.result,
    # completely untouched by that narrative text.
    assert framed.result["original_figures"] == real_figures
    assert framed.result["original_figures"] is not framed.result["narrative"]


def test_frame_candidate_sets_judgement_and_provisional():
    candidate = _make_candidate({"expected_risk_reduction_pct": 3.2})
    framed = frame_candidate(candidate, StubExplanationGenerator())
    assert framed.information_class == InformationClass.JUDGEMENT
    assert framed.validation_status == ValidationStatus.PROVISIONAL


def test_frame_candidate_includes_candidate_id_in_dependencies():
    candidate = _make_candidate({"expected_risk_reduction_pct": 3.2})
    framed = frame_candidate(candidate, StubExplanationGenerator())
    assert candidate.id in framed.dependencies


def test_frame_candidate_includes_upstream_context_ids_in_dependencies():
    candidate = _make_candidate({"expected_risk_reduction_pct": 3.2})
    upstream = _make_candidate({"forecast": 0.05})
    framed = frame_candidate(candidate, StubExplanationGenerator(), upstream_context=[upstream])
    assert candidate.id in framed.dependencies
    assert upstream.id in framed.dependencies


def test_generator_never_receives_the_candidates_figures():
    """
    Confirms the structural guarantee at its source: the context dict
    passed to generate() never contains candidate.result anywhere.
    """
    seen_contexts = []

    class RecordingGenerator:
        def generate(self, prompt: str, context: dict) -> str:
            seen_contexts.append((prompt, context))
            return "narrative"

    real_figures = {"expected_risk_reduction_pct": 3.2}
    candidate = _make_candidate(real_figures)
    frame_candidate(candidate, RecordingGenerator())

    assert len(seen_contexts) == 1
    prompt, context = seen_contexts[0]
    assert real_figures not in context.values()
    assert "3.2" not in prompt
    for value in context.values():
        assert value != real_figures
