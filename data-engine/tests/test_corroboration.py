"""
Tests for corroborate_fact (ANALYTICAL_CONTRACT_SPEC.md, Section 4a) — in
particular the shared-origin rejection rule.
"""

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_data import corroborate_fact


def _make_uap(
    source: str,
    information_class: InformationClass = InformationClass.FACT,
    validation_status: ValidationStatus = ValidationStatus.PROVISIONAL,
) -> UAP:
    return UAP(
        subject="illustrative claim",
        information_class=information_class,
        validation_status=validation_status,
        result="illustrative claim result",
        source=source,
        producer="data-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_successful_corroboration_with_one_independent_source():
    provisional_fact = _make_uap(source="Outlet A")
    candidate = _make_uap(source="Outlet B")

    result = corroborate_fact(provisional_fact, [candidate])

    assert result.validation_status == ValidationStatus.VERIFIED
    assert any("Outlet B" in entry for entry in result.evidence)


def test_shared_origin_candidates_do_not_corroborate():
    """
    The critical test: provisional_fact and both candidates all share the
    identical `source` value — a republication scenario
    (ANALYTICAL_CONTRACT_SPEC.md Section 4a's explicit example). This
    must NOT corroborate.
    """
    provisional_fact = _make_uap(source="Wire Service X")
    candidate_1 = _make_uap(source="Wire Service X")
    candidate_2 = _make_uap(source="Wire Service X")

    result = corroborate_fact(provisional_fact, [candidate_1, candidate_2])

    assert result.validation_status == ValidationStatus.PROVISIONAL


def test_no_candidate_sources_remains_provisional():
    provisional_fact = _make_uap(source="Outlet A")

    result = corroborate_fact(provisional_fact, [])

    assert result.validation_status == ValidationStatus.PROVISIONAL


def test_structured_cross_check_with_single_verified_fact():
    provisional_fact = _make_uap(source="Outlet A")
    verified_fact = _make_uap(
        source="Official Statistics Release",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
    )

    result = corroborate_fact(provisional_fact, [verified_fact])

    assert result.validation_status == ValidationStatus.VERIFIED
    assert any("structured cross-check" in entry for entry in result.evidence)


def test_two_candidates_sharing_a_source_with_each_other_count_once_not_twice():
    """
    Two candidates whose source differs from provisional_fact's, but
    matches each other's, still succeed via that one genuinely
    independent source — but must be recorded once, not twice
    (Section 4a: "so that two republications of the same wire story or
    press release cannot corroborate each other" into double-counting).
    """
    provisional_fact = _make_uap(source="Outlet A")
    candidate_1 = _make_uap(source="Outlet B")
    candidate_2 = _make_uap(source="Outlet B")

    result = corroborate_fact(provisional_fact, [candidate_1, candidate_2])

    assert result.validation_status == ValidationStatus.VERIFIED
    outlet_b_entries = [entry for entry in result.evidence if "Outlet B" in entry]
    assert len(outlet_b_entries) == 1


def test_does_not_mutate_provisional_fact_or_candidates():
    provisional_fact = _make_uap(source="Outlet A")
    candidate = _make_uap(source="Outlet B")

    provisional_fact_before = provisional_fact.model_dump()
    candidate_before = candidate.model_dump()

    corroborate_fact(provisional_fact, [candidate])

    assert provisional_fact.model_dump() == provisional_fact_before
    assert candidate.model_dump() == candidate_before


def test_raises_clear_error_when_provisional_fact_is_not_fact_provisional():
    not_provisional = _make_uap(
        source="Outlet A",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
    )
    with pytest.raises(ValueError):
        corroborate_fact(not_provisional, [_make_uap(source="Outlet B")])


def test_raises_clear_error_when_provisional_fact_is_not_information_class_fact():
    an_estimate = _make_uap(
        source="Outlet A",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
    )
    with pytest.raises(ValueError):
        corroborate_fact(an_estimate, [_make_uap(source="Outlet B")])
