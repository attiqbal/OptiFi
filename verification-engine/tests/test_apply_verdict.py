"""
Tests for apply_verdict (VERIFICATION_FRAMEWORK.md, Section 4).
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_verification import Verdict, VerdictType, apply_verdict


def _make_uap(validation_status: ValidationStatus = ValidationStatus.PROVISIONAL) -> UAP:
    return UAP(
        subject="test subject",
        information_class=InformationClass.FACT,
        validation_status=validation_status,
        result="test result",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_pass_moves_validation_status_to_verified():
    uap = _make_uap(validation_status=ValidationStatus.PROVISIONAL)
    result = apply_verdict(uap, Verdict(verdict_type=VerdictType.PASS))
    assert result.validation_status == ValidationStatus.VERIFIED


def test_pass_with_caution_leaves_validation_status_unchanged_but_notes_caution():
    uap = _make_uap(validation_status=ValidationStatus.PROVISIONAL)
    verdict = Verdict(
        verdict_type=VerdictType.PASS_WITH_CAUTION,
        reasons=["a dependency was itself only PROVISIONAL"],
    )
    result = apply_verdict(uap, verdict)
    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert any("PROVISIONAL" in note for note in result.limitations)


def test_flag_sets_validation_status_to_flagged_status():
    uap = _make_uap(validation_status=ValidationStatus.PROVISIONAL)
    verdict = Verdict(
        verdict_type=VerdictType.FLAG,
        reasons=["conflicts with another VERIFIED output"],
        flagged_status=ValidationStatus.CONFLICTED,
    )
    result = apply_verdict(uap, verdict)
    assert result.validation_status == ValidationStatus.CONFLICTED


def test_reject_sets_validation_status_to_rejected():
    uap = _make_uap(validation_status=ValidationStatus.PROVISIONAL)
    result = apply_verdict(uap, Verdict(verdict_type=VerdictType.REJECT, reasons=["failed"]))
    assert result.validation_status == ValidationStatus.REJECTED


def test_apply_verdict_does_not_mutate_input():
    uap = _make_uap(validation_status=ValidationStatus.PROVISIONAL)
    before = uap.model_dump()

    apply_verdict(uap, Verdict(verdict_type=VerdictType.PASS))

    assert uap.model_dump() == before
