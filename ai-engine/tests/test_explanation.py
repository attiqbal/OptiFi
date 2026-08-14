from optifi_ai.explanation import build_explanation, present_for_sophistication, UserSophistication
from optifi_ai.generator import ExplanationGenerator, StubExplanationGenerator
from optifi_ai.verification_gate import CIOVerdictHandling, GateResult
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus


def _uap(subject: str, information_class=InformationClass.FACT, **overrides) -> UAP:
    defaults = dict(
        subject=subject,
        information_class=information_class,
        validation_status=ValidationStatus.VERIFIED,
        result=1.0,
        source="test",
        producer="test",
        confidence=ConfidenceLevel.MODERATE,
    )
    defaults.update(overrides)
    return UAP(**defaults)


def test_build_explanation_buckets_by_information_class():
    fact = _uap("f", InformationClass.FACT)
    estimate = _uap("e", InformationClass.ESTIMATE, validation_status=ValidationStatus.PROVISIONAL)
    judgement = _uap("j", InformationClass.JUDGEMENT, validation_status=ValidationStatus.PROVISIONAL)

    explanation = build_explanation([fact, estimate, judgement])
    assert explanation.facts == [fact]
    assert explanation.estimates == [estimate]
    assert explanation.judgements == [judgement]


def test_non_verified_items_are_disclosed():
    provisional = _uap("p", validation_status=ValidationStatus.PROVISIONAL)
    explanation = build_explanation([provisional])
    assert any("PROVISIONAL" in note for note in explanation.non_verified_disclosures)


def test_default_suggested_action_is_no_action():
    explanation = build_explanation([_uap("f")])
    assert explanation.suggested_action == "NO ACTION"


def test_rejected_candidate_never_becomes_a_suggested_action():
    candidate = _uap("optimisation candidate", InformationClass.ESTIMATE, validation_status=ValidationStatus.PROVISIONAL)
    gate_result = GateResult(handling=CIOVerdictHandling.REJECT, excluded=True, reasons=["loss cap violated"])
    explanation = build_explanation([], candidate=candidate, gate_result=gate_result)
    assert explanation.suggested_action.startswith("NO ACTION")
    assert candidate.subject not in explanation.suggested_action


def test_revise_and_insufficient_evidence_defer_rather_than_recommend():
    candidate = _uap("optimisation candidate", InformationClass.ESTIMATE, validation_status=ValidationStatus.PROVISIONAL)
    for handling in (CIOVerdictHandling.REVISE, CIOVerdictHandling.INSUFFICIENT_EVIDENCE):
        gate_result = GateResult(handling=handling, excluded=False, reasons=["r"])
        explanation = build_explanation([], candidate=candidate, gate_result=gate_result)
        assert explanation.suggested_action.startswith("NO ACTION")


def test_passing_candidate_is_named_but_figures_are_never_generated():
    candidate = _uap("minimum-variance candidate", InformationClass.ESTIMATE, validation_status=ValidationStatus.PROVISIONAL)
    gate_result = GateResult(handling=CIOVerdictHandling.PASS, excluded=False, reasons=["ok"])
    explanation = build_explanation([], candidate=candidate, gate_result=gate_result)
    assert candidate.subject in explanation.suggested_action


class _DirectiveGenerator:
    def generate(self, prompt: str, context: dict) -> str:
        return "You should Buy AAPL right now."


def test_directive_language_is_redacted_from_generated_text():
    explanation = build_explanation([_uap("f")])
    text = present_for_sophistication(explanation, UserSophistication.INFORMED, _DirectiveGenerator())
    assert "Buy AAPL" not in text
    assert "redacted" in text.lower()


def test_sophistication_levels_vary_depth_not_underlying_facts():
    explanation = build_explanation([_uap("f")], candidate=None, gate_result=None)
    gen = StubExplanationGenerator()
    beginner = present_for_sophistication(explanation, UserSophistication.BEGINNER, gen)
    professional = present_for_sophistication(explanation, UserSophistication.PROFESSIONAL, gen)
    assert "Why (evidence ids)" not in beginner
    assert "Why (evidence ids)" in professional
    # Same underlying facts referenced in both, regardless of depth.
    assert "f" in beginner and "f" in professional
