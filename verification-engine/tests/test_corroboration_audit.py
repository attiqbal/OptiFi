"""
Tests for audit_corroboration (VERIFICATION_FRAMEWORK.md, Section 5.1/3) —
an independent re-derivation of ANALYTICAL_CONTRACT_SPEC.md Section 4a's
corroboration logic, deliberately not calling data-engine's
corroborate_fact.
"""

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_verification import VerdictType, audit_corroboration


def _make_uap(
    source: str,
    information_class: InformationClass = InformationClass.FACT,
    validation_status: ValidationStatus = ValidationStatus.VERIFIED,
) -> UAP:
    return UAP(
        subject="illustrative audited claim",
        information_class=information_class,
        validation_status=validation_status,
        result="illustrative claim result",
        source=source,
        producer="data-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_independently_corroborated_but_unverified_source_produces_pass_with_caution():
    """
    Verdict-gap fix: the confirming source is genuinely independent (a
    different origin, satisfying Section 4a's rule), but is itself only
    PROVISIONAL -- VERIFICATION_FRAMEWORK.md Section 4's own literal
    example of PASS WITH CAUTION ("a dependency was itself only
    PROVISIONAL"). Previously this collapsed into a clean, uncaveated
    PASS; now it must not.
    """
    verified_fact = _make_uap(source="Outlet A")
    sources_used = [_make_uap(source="Outlet B", validation_status=ValidationStatus.PROVISIONAL)]

    verdict = audit_corroboration(verified_fact, sources_used)

    assert verdict.verdict_type == VerdictType.PASS_WITH_CAUTION
    assert any("PROVISIONAL" in reason for reason in verdict.reasons)


def test_independent_source_that_is_itself_verified_produces_clean_pass():
    """
    Companion/control case for the fix above: when the independent
    source is ITSELF already VERIFIED (even without being a structured
    FACT+VERIFIED cross-check), there is nothing unsettled to caveat --
    a clean PASS is still correct.
    """
    verified_fact = _make_uap(source="Outlet A")
    sources_used = [
        _make_uap(
            source="Outlet B",
            information_class=InformationClass.ESTIMATE,  # not FACT, so not a structured cross-check
            validation_status=ValidationStatus.VERIFIED,
        )
    ]

    verdict = audit_corroboration(verified_fact, sources_used)

    assert verdict.verdict_type == VerdictType.PASS


def test_should_never_have_passed_case_is_caught():
    """
    The single most important test in this module: a fact hand-marked
    VERIFIED whose sources_used all actually share the fact's own
    source — this should never have passed corroborate_fact's own logic
    in the first place, and this audit exists specifically to catch a
    claim like this that somehow got through.
    """
    verified_fact = _make_uap(source="Wire Service X", validation_status=ValidationStatus.VERIFIED)
    shared_origin_source_1 = _make_uap(
        source="Wire Service X", validation_status=ValidationStatus.PROVISIONAL
    )
    shared_origin_source_2 = _make_uap(
        source="Wire Service X", validation_status=ValidationStatus.PROVISIONAL
    )

    verdict = audit_corroboration(
        verified_fact, [shared_origin_source_1, shared_origin_source_2]
    )

    assert verdict.verdict_type == VerdictType.REJECT
    assert verdict.failure_category is not None
    assert verdict.failure_category.value == "DATA_QUALITY"


def test_structured_cross_check_case_passes():
    verified_fact = _make_uap(source="Outlet A", validation_status=ValidationStatus.VERIFIED)
    structured_cross_check_source = _make_uap(
        source="Outlet A",  # same source as the fact itself
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,  # but itself already VERIFIED
    )

    verdict = audit_corroboration(verified_fact, [structured_cross_check_source])

    assert verdict.verdict_type == VerdictType.PASS


def test_raises_clear_error_for_non_verified_input():
    provisional_fact = _make_uap(source="Outlet A", validation_status=ValidationStatus.PROVISIONAL)
    with pytest.raises(ValueError):
        audit_corroboration(provisional_fact, [_make_uap(source="Outlet B")])


def test_raises_clear_error_for_non_fact_input():
    an_estimate = _make_uap(
        source="Outlet A",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.VERIFIED,
    )
    with pytest.raises(ValueError):
        audit_corroboration(an_estimate, [_make_uap(source="Outlet B")])
