"""
Tests for the UAP model (ANALYTICAL_CONTRACT_SPEC.md, Section 5).
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus


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
