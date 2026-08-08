"""
Tests for the Verdict/VerdictType/FailureCategory foundation
(VERIFICATION_FRAMEWORK.md, Section 4/5.7).
"""

import pytest
from optifi_shared import ValidationStatus
from pydantic import ValidationError

from optifi_verification import FailureCategory, Verdict, VerdictType


def test_pass_verdict_constructs():
    verdict = Verdict(verdict_type=VerdictType.PASS)
    assert verdict.verdict_type == VerdictType.PASS
    assert verdict.failure_category is None


def test_reject_verdict_with_multiple_reasons_and_category():
    verdict = Verdict(
        verdict_type=VerdictType.REJECT,
        reasons=["reason one", "reason two"],
        failure_category=FailureCategory.DATA_QUALITY,
    )
    assert len(verdict.reasons) == 2
    assert verdict.failure_category == FailureCategory.DATA_QUALITY


def test_flag_verdict_requires_flagged_status():
    with pytest.raises(ValidationError):
        Verdict(verdict_type=VerdictType.FLAG, reasons=["some issue"])


def test_flag_verdict_with_valid_flagged_status_constructs():
    verdict = Verdict(
        verdict_type=VerdictType.FLAG,
        reasons=["dependency was itself only PROVISIONAL"],
        flagged_status=ValidationStatus.INCOMPLETE,
    )
    assert verdict.flagged_status == ValidationStatus.INCOMPLETE


def test_flag_verdict_rejects_invalid_flagged_status():
    with pytest.raises(ValidationError):
        Verdict(
            verdict_type=VerdictType.FLAG,
            reasons=["some issue"],
            flagged_status=ValidationStatus.VERIFIED,
        )
