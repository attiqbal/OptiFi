"""
Tests for the UAP model (ANALYTICAL_CONTRACT_SPEC.md, Section 5).
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from optifi_shared import ConfidenceLevel, InformationClass, supersede, UAP, ValidationStatus


def _full_uap_kwargs() -> dict:
    """Valid data covering every field on the UAP model."""
    return dict(
        id="fixed-id-for-test",
        subject="US recession probability, 12-month horizon",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=0.32,
        source="illustrative test source",
        producer="forecast-engine / econometric model",
        evidence=["illustrative evidence pointer"],
        evidence_as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
        generated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        confidence=ConfidenceLevel.MODERATE,
        assumptions=["stable policy regime"],
        limitations=["does not account for external shocks"],
        dependencies=["upstream-uap-id-1"],
        provenance_chain=["fact-uap-id-1", "fact-uap-id-2"],
        disagreement_set_ref="recession-probability-2026-set",
        supersedes=["earlier-uap-id"],
    )


def test_uap_constructs_with_valid_data_for_every_field():
    uap = UAP(**_full_uap_kwargs())

    assert uap.id == "fixed-id-for-test"
    assert uap.subject == "US recession probability, 12-month horizon"
    assert uap.information_class == InformationClass.ESTIMATE
    assert uap.validation_status == ValidationStatus.PROVISIONAL
    assert uap.result == 0.32
    assert uap.source == "illustrative test source"
    assert uap.producer == "forecast-engine / econometric model"
    assert uap.evidence == ["illustrative evidence pointer"]
    assert uap.evidence_as_of == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert uap.generated_at == datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert uap.confidence == ConfidenceLevel.MODERATE
    assert uap.assumptions == ["stable policy regime"]
    assert uap.limitations == ["does not account for external shocks"]
    assert uap.dependencies == ["upstream-uap-id-1"]
    assert uap.provenance_chain == ["fact-uap-id-1", "fact-uap-id-2"]
    assert uap.disagreement_set_ref == "recession-probability-2026-set"
    assert uap.supersedes == ["earlier-uap-id"]


@pytest.mark.parametrize(
    "missing_field",
    ["subject", "information_class", "validation_status", "result", "source", "producer", "confidence"],
)
def test_missing_required_field_raises_error(missing_field):
    kwargs = _full_uap_kwargs()
    del kwargs[missing_field]
    del kwargs["id"]  # id is never required; keep the test focused on one field

    with pytest.raises(ValidationError):
        UAP(**kwargs)


def test_invalid_information_class_raises_error():
    kwargs = _full_uap_kwargs()
    kwargs["information_class"] = "NOT_A_REAL_CLASS"

    with pytest.raises(ValidationError):
        UAP(**kwargs)


def test_invalid_validation_status_raises_error():
    kwargs = _full_uap_kwargs()
    kwargs["validation_status"] = "NOT_A_REAL_STATUS"

    with pytest.raises(ValidationError):
        UAP(**kwargs)


def test_confidence_rejects_arbitrary_string():
    kwargs = _full_uap_kwargs()
    kwargs["confidence"] = "illustrative example only"

    with pytest.raises(ValidationError):
        UAP(**kwargs)


def test_confidence_only_accepts_a_valid_confidence_level():
    for level in ConfidenceLevel:
        kwargs = _full_uap_kwargs()
        kwargs["confidence"] = level
        if level == ConfidenceLevel.HIGH:
            # HIGH requires a settled validation_status (see
            # test_high_confidence_requires_settled_status below) —
            # _full_uap_kwargs()'s default PROVISIONAL wouldn't allow it.
            kwargs["validation_status"] = ValidationStatus.VERIFIED
        assert UAP(**kwargs).confidence == level


def test_two_instances_have_different_auto_generated_ids():
    minimal_kwargs = dict(
        subject="test subject",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=100,
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.HIGH,
    )

    first = UAP(**minimal_kwargs)
    second = UAP(**minimal_kwargs)

    assert first.id != second.id


# --- HIGH confidence requires a settled validation_status ---


def test_high_confidence_requires_settled_status():
    kwargs = _full_uap_kwargs()
    kwargs["confidence"] = ConfidenceLevel.HIGH
    kwargs["validation_status"] = ValidationStatus.PROVISIONAL  # the original adversarial case

    with pytest.raises(ValidationError, match="HIGH"):
        UAP(**kwargs)


@pytest.mark.parametrize("status", [ValidationStatus.VERIFIED, ValidationStatus.SUPERSEDED])
def test_high_confidence_allowed_for_settled_statuses(status):
    kwargs = _full_uap_kwargs()
    kwargs["confidence"] = ConfidenceLevel.HIGH
    kwargs["validation_status"] = status
    assert UAP(**kwargs).confidence == ConfidenceLevel.HIGH


@pytest.mark.parametrize(
    "status",
    [
        ValidationStatus.PROVISIONAL,
        ValidationStatus.CONFLICTED,
        ValidationStatus.STALE,
        ValidationStatus.INCOMPLETE,
        ValidationStatus.REJECTED,
    ],
)
def test_high_confidence_rejected_for_every_unsettled_status(status):
    kwargs = _full_uap_kwargs()
    kwargs["confidence"] = ConfidenceLevel.HIGH
    kwargs["validation_status"] = status
    with pytest.raises(ValidationError, match="HIGH"):
        UAP(**kwargs)


@pytest.mark.parametrize(
    "status",
    [
        ValidationStatus.PROVISIONAL,
        ValidationStatus.CONFLICTED,
        ValidationStatus.STALE,
        ValidationStatus.INCOMPLETE,
        ValidationStatus.REJECTED,
    ],
)
@pytest.mark.parametrize("confidence", [ConfidenceLevel.MODERATE, ConfidenceLevel.LOW])
def test_moderate_and_low_confidence_remain_valid_for_every_unsettled_status(status, confidence):
    kwargs = _full_uap_kwargs()
    kwargs["confidence"] = confidence
    kwargs["validation_status"] = status
    uap = UAP(**kwargs)
    assert uap.confidence == confidence
    assert uap.validation_status == status


def test_provenance_chain_and_dependencies_default_to_empty_list():
    uap = UAP(
        subject="test subject",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=100,
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.HIGH,
    )

    assert uap.provenance_chain == []
    assert uap.dependencies == []
    assert uap.evidence == []
    assert uap.assumptions == []
    assert uap.limitations == []
    assert uap.supersedes == []
    assert uap.disagreement_set_ref is None
    assert uap.evidence_as_of is None
    # Phase E1 time-semantics fields: all optional, all default to None —
    # confirms every pre-existing construction call across the codebase
    # (none of which pass these new fields) remains valid unchanged.
    assert uap.observation_time is None
    assert uap.observation_period_end is None
    assert uap.publication_time is None
    assert uap.retrieval_time is None
    assert uap.as_of is None
    assert uap.vintage is None


# --- Phase E1: time-semantics fields ---


def test_time_semantics_fields_construct_and_are_independently_settable():
    uap = UAP(
        subject="Q3 GDP, UK",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result=0.4,
        source="ONS",
        producer="data-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
        observation_time=datetime(2026, 7, 1, tzinfo=timezone.utc),
        observation_period_end=datetime(2026, 9, 30, tzinfo=timezone.utc),
        publication_time=datetime(2026, 10, 15, tzinfo=timezone.utc),
        retrieval_time=datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc),
        as_of=datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc),
        vintage="advance estimate",
    )
    assert uap.observation_time == datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert uap.observation_period_end == datetime(2026, 9, 30, tzinfo=timezone.utc)
    assert uap.publication_time == datetime(2026, 10, 15, tzinfo=timezone.utc)
    assert uap.retrieval_time == datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)
    assert uap.as_of == datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)
    assert uap.vintage == "advance estimate"


# --- Phase E1: supersede() ---


def _make_gdp_uap(vintage: str, result: float, **overrides) -> UAP:
    defaults = dict(
        subject="Q3 GDP, UK",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=result,
        source="ONS",
        producer="data-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
        vintage=vintage,
    )
    defaults.update(overrides)
    return UAP(**defaults)


def test_supersede_marks_old_as_superseded_without_mutating_it():
    old = _make_gdp_uap("advance estimate", 0.4)
    new = _make_gdp_uap("second estimate", 0.5)

    new_linked, old_superseded = supersede(old, new)

    # Original `old` object is untouched — historical information is
    # never overwritten in place.
    assert old.validation_status == ValidationStatus.VERIFIED
    assert old_superseded.validation_status == ValidationStatus.SUPERSEDED
    assert old_superseded is not old
    assert old_superseded.result == 0.4  # the original value is preserved, not lost


def test_supersede_links_new_packet_to_old_via_supersedes():
    old = _make_gdp_uap("advance estimate", 0.4)
    new = _make_gdp_uap("second estimate", 0.5)

    new_linked, _ = supersede(old, new)

    assert old.id in new_linked.supersedes
    # No forward-pointing field on the old packet itself (per spec).
    old_dict = old.model_dump()
    assert "supersedes_by" not in old_dict


def test_supersede_is_idempotent_if_new_already_references_old():
    old = _make_gdp_uap("advance estimate", 0.4)
    new = _make_gdp_uap("second estimate", 0.5, supersedes=[old.id])

    new_linked, _ = supersede(old, new)

    assert new_linked.supersedes.count(old.id) == 1


def test_supersede_rejects_mismatched_subject():
    old = _make_gdp_uap("advance estimate", 0.4)
    different_subject = _make_gdp_uap("second estimate", 0.5, subject="Q3 CPI, UK")

    with pytest.raises(ValueError, match="subject"):
        supersede(old, different_subject)


def test_supersede_rejects_double_supersession():
    old = _make_gdp_uap("advance estimate", 0.4)
    second = _make_gdp_uap("second estimate", 0.5)
    _, old_superseded = supersede(old, second)

    third = _make_gdp_uap("final", 0.55)
    with pytest.raises(ValueError, match="already SUPERSEDED"):
        supersede(old_superseded, third)
