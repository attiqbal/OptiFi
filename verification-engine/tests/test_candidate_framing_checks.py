"""
Tests for verify_candidate_framing_unaltered (VERIFICATION_FRAMEWORK.md
Section 6) — an independent check that ai-engine's Stage 10 candidate
framing hasn't altered the figures optimisation-engine produced.

optifi_ai is only a [dev]/test dependency of this package (see
pyproject.toml) — used here to produce one genuine frame_candidate output
to test against. The production check in candidate_framing_checks.py does
not import optifi_ai at all.
"""

from optifi_ai import StubExplanationGenerator, frame_candidate
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_verification import FailureCategory, VerdictType, verify_candidate_framing_unaltered


def _make_candidate(result) -> UAP:
    return UAP(
        subject="reduce duration exposure",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.VERIFIED,
        result=result,
        source="optimisation-engine",
        producer="optimisation-engine (test)",
        confidence=ConfidenceLevel.HIGH,
    )


def _make_framed(subject: str, dependencies: list[str], result) -> UAP:
    # MODERATE, not HIGH: PROVISIONAL (frame_candidate's own output
    # status) does not permit HIGH confidence under UAP's own
    # model-level guardrail (shared/optifi_shared/uap.py).
    return UAP(
        subject=subject,
        information_class=InformationClass.JUDGEMENT,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="ai-engine candidate framing (test)",
        producer="ai-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=dependencies,
    )


def test_genuine_unaltered_framing_from_real_frame_candidate_passes():
    candidate = _make_candidate(
        {"expected_risk_reduction_pct": 3.2, "expected_return_impact_pct": 0.4}
    )
    framed = frame_candidate(candidate, StubExplanationGenerator())

    verdict = verify_candidate_framing_unaltered(candidate, framed)

    assert verdict.verdict_type == VerdictType.PASS


def test_hand_altered_figure_is_rejected_and_named():
    """
    Not produced by the real frame_candidate — a hand-made framed_output
    simulating a future regression where the structural guarantee is
    broken, to prove this check catches it independently rather than
    trusting ai-engine's own claim.
    """
    candidate = _make_candidate(
        {"expected_risk_reduction_pct": 3.2, "expected_return_impact_pct": 0.4}
    )
    tampered = _make_framed(
        candidate.subject,
        [candidate.id],
        {
            "narrative": "this action reduces risk substantially",
            "original_figures": {
                "expected_risk_reduction_pct": 47.5,  # altered
                "expected_return_impact_pct": 0.4,  # unaltered
            },
        },
    )

    verdict = verify_candidate_framing_unaltered(candidate, tampered)

    assert verdict.verdict_type == VerdictType.REJECT
    assert verdict.failure_category == FailureCategory.DATA_QUALITY
    reasons_joined = " ".join(verdict.reasons)
    assert "expected_risk_reduction_pct" in reasons_joined
    assert "3.2" in reasons_joined and "47.5" in reasons_joined
    # the unaltered figure must not be reported as a discrepancy
    assert "expected_return_impact_pct" not in reasons_joined


def test_multiple_altered_figures_are_all_named():
    candidate = _make_candidate({"a": 1.0, "b": 2.0, "c": 3.0})
    tampered = _make_framed(
        candidate.subject,
        [candidate.id],
        {"narrative": "...", "original_figures": {"a": 999.0, "b": 2.0, "c": -1.0}},
    )

    verdict = verify_candidate_framing_unaltered(candidate, tampered)

    assert verdict.verdict_type == VerdictType.REJECT
    reasons_joined = " ".join(verdict.reasons)
    assert "'a'" in reasons_joined
    assert "'c'" in reasons_joined
    assert "'b'" not in reasons_joined


def test_missing_original_figures_key_rejected_not_crashed():
    candidate = _make_candidate({"a": 1.0})
    malformed = _make_framed(
        candidate.subject, [candidate.id], {"narrative": "some narrative, no figures at all"}
    )

    verdict = verify_candidate_framing_unaltered(candidate, malformed)

    assert verdict.verdict_type == VerdictType.REJECT
    assert verdict.failure_category == FailureCategory.DATA_QUALITY
    assert len(verdict.reasons) >= 1


def test_non_dict_result_rejected_not_crashed():
    candidate = _make_candidate({"a": 1.0})
    malformed = _make_framed(
        candidate.subject, [candidate.id], "just a plain narrative string, not a dict at all"
    )

    verdict = verify_candidate_framing_unaltered(candidate, malformed)

    assert verdict.verdict_type == VerdictType.REJECT
    assert verdict.failure_category == FailureCategory.DATA_QUALITY


def test_scalar_figures_that_differ_are_reported():
    candidate = _make_candidate(3.2)
    tampered = _make_framed(
        candidate.subject, [candidate.id], {"narrative": "...", "original_figures": 47.5}
    )

    verdict = verify_candidate_framing_unaltered(candidate, tampered)

    assert verdict.verdict_type == VerdictType.REJECT
    reasons_joined = " ".join(verdict.reasons)
    assert "3.2" in reasons_joined and "47.5" in reasons_joined
