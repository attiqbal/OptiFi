"""
Attack 4 — Confidence Inflation.

`confidence` (Section 5 of ANALYTICAL_CONTRACT_SPEC.md) and
`validation_status` (Section 4) are explicitly documented as two
independent axes. This attack originally found that "independent" meant
"nothing anywhere checks whether a specific combination is internally
consistent" — a PROVISIONAL, single-sourced, uncorroborated FACT could
freely claim HIGH confidence with zero pushback anywhere in the system.

UPDATE (post-fix): UAP now has a model_validator
(shared/optifi_shared/uap.py) requiring HIGH confidence to pair only with
a settled validation_status (VERIFIED or SUPERSEDED) — every other status
caps confidence at MODERATE. See
shared/tests/test_uap.py::test_high_confidence_requires_settled_status
and its neighbouring tests for the complete matrix.
"""

import pytest
from pydantic import ValidationError

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_verification import (
    audit_corroboration,
    check_provenance_resolvable,
    verify_optimisation_candidate,
)


def test_re_test_the_original_inflated_fact_now_raises():
    """
    RE-TEST (post-fix), the exact original construction: a PROVISIONAL,
    single-sourced, uncorroborated FACT claiming HIGH confidence no
    longer constructs at all.
    """
    with pytest.raises(ValidationError, match="HIGH"):
        UAP(
            subject="Bank of England signalled a rate cut",
            information_class=InformationClass.FACT,
            validation_status=ValidationStatus.PROVISIONAL,  # single-sourced, uncorroborated
            result="Bank of England signalled a rate cut",
            source="Illustrative Wire Service — not a real data source",
            producer="data-engine (test)",
            confidence=ConfidenceLevel.HIGH,  # claims the opposite
        )


def test_the_same_fact_construction_succeeds_once_genuinely_verified():
    """
    The legitimate version of the original scenario: once the fact is
    actually VERIFIED (settled), HIGH confidence is a permitted, honest
    claim — the fix gates the combination, it doesn't ban HIGH outright.
    """
    verified_fact = UAP(
        subject="Bank of England signalled a rate cut",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result="Bank of England signalled a rate cut",
        source="Illustrative Wire Service — not a real data source",
        producer="data-engine (test)",
        confidence=ConfidenceLevel.HIGH,
    )
    assert verified_fact.validation_status == ValidationStatus.VERIFIED
    assert verified_fact.confidence == ConfidenceLevel.HIGH


def test_verification_engine_checks_are_unaffected_since_the_gap_is_now_closed_upstream():
    """
    Extends the original finding's own observation — none of
    verification-engine's checks inspect `confidence` — but notes that
    this no longer matters for the inflated-PROVISIONAL case specifically,
    since that combination can no longer exist as a constructed UAP for
    any of these checks to receive in the first place. The checks
    themselves are genuinely unchanged (out of this task's scope), so
    they're re-run here against a validly-constructed MODERATE-confidence
    PROVISIONAL fact instead, to confirm nothing else broke.
    """
    valid_fact = UAP(
        subject="Bank of England signalled a rate cut",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result="Bank of England signalled a rate cut",
        source="Illustrative Wire Service — not a real data source",
        producer="data-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
    )

    provenance_verdict = check_provenance_resolvable(valid_fact, known_packets={valid_fact.id: valid_fact})
    assert provenance_verdict.verdict_type.value == "PASS"

    with pytest.raises(ValueError):
        audit_corroboration(valid_fact, sources_used=[])

    verdict = verify_optimisation_candidate(
        {"A": 1.0}, {"A": 0.05}, target_return=0.05, min_weight=0.0, max_weight=1.0
    )
    assert verdict.verdict_type.value == "PASS"


def test_re_test_only_settled_statuses_permit_high_moderate_and_low_remain_unrestricted():
    """
    RE-TEST (post-fix) of the original broad sweep: every
    validation_status/confidence combination used to construct
    successfully. Now, HIGH is gated to VERIFIED/SUPERSEDED specifically
    — MODERATE and LOW remain fully unrestricted across every status,
    confirming the fix is precisely scoped to HIGH, not a general
    tightening of the model.
    """
    settled_statuses = {ValidationStatus.VERIFIED, ValidationStatus.SUPERSEDED}

    for validation_status in ValidationStatus:
        for confidence in ConfidenceLevel:
            kwargs = dict(
                subject="test",
                information_class=InformationClass.FACT,
                validation_status=validation_status,
                result="test",
                source="test source",
                producer="test producer",
                confidence=confidence,
            )
            if confidence == ConfidenceLevel.HIGH and validation_status not in settled_statuses:
                with pytest.raises(ValidationError, match="HIGH"):
                    UAP(**kwargs)
            else:
                uap = UAP(**kwargs)
                assert uap.validation_status == validation_status
                assert uap.confidence == confidence
