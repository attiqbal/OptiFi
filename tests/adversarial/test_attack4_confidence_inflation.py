"""
Attack 4 — Confidence Inflation.

`confidence` (Section 5 of ANALYTICAL_CONTRACT_SPEC.md) and
`validation_status` (Section 4) are explicitly documented as two
independent axes. This attack asks: independent in the sense of "not
conflated in meaning" (the documented intent), or independent in the
sense of "nothing anywhere checks whether a specific combination is
internally consistent"? A PROVISIONAL, single-sourced, uncorroborated
FACT claiming HIGH confidence is a specific, testable case of the
latter.
"""

import pytest

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_verification import (
    audit_corroboration,
    check_provenance_resolvable,
    verify_optimisation_candidate,
)


def _inflated_fact() -> UAP:
    return UAP(
        subject="Bank of England signalled a rate cut",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,  # single-sourced, uncorroborated
        result="Bank of England signalled a rate cut",
        source="Illustrative Wire Service — not a real data source",
        producer="data-engine (test)",
        confidence=ConfidenceLevel.HIGH,  # claims the opposite
    )


def test_pydantic_model_construction_raises_no_error():
    """
    THE ADVERSARIAL FINDING: constructing a PROVISIONAL FACT with
    confidence=HIGH raises nothing at all — no ValidationError, no
    warning. UAP has no model_validator relating these two fields (see
    shared/optifi_shared/uap.py — confidence and validation_status are
    each validated independently, never against each other).
    """
    inflated = _inflated_fact()  # would raise here if anything guarded this
    assert inflated.validation_status == ValidationStatus.PROVISIONAL
    assert inflated.confidence == ConfidenceLevel.HIGH


def test_no_verification_engine_check_notices_the_inconsistency_either():
    """
    Extends the finding across verification-engine: none of its checks
    inspect `confidence` at all, so an inflated-confidence PROVISIONAL
    fact sails through every one of them with no flag, note, or
    downgrade — not because it was checked and found acceptable, but
    because confidence vs. validation_status consistency is not
    something any of these functions look at.
    """
    inflated = _inflated_fact()

    # check_provenance_resolvable: only inspects provenance_chain.
    provenance_verdict = check_provenance_resolvable(inflated, known_packets={inflated.id: inflated})
    assert provenance_verdict.verdict_type.value == "PASS"

    # audit_corroboration requires VERIFIED input to even run — so the
    # inflated PROVISIONAL fact can't reach this check at all yet, which
    # itself means nothing here catches it either; it simply isn't in
    # scope.
    with pytest.raises(ValueError):
        audit_corroboration(inflated, sources_used=[])

    # verify_optimisation_candidate operates on plain weight dicts, not
    # UAPs — confidence never even enters its inputs. Included to show
    # the inconsistency has no surface area anywhere in this function
    # either, not because it was deliberately excluded from scope here.
    verdict = verify_optimisation_candidate(
        {"A": 1.0}, {"A": 0.05}, target_return=0.05, min_weight=0.0, max_weight=1.0
    )
    assert verdict.verdict_type.value == "PASS"


def test_confidence_can_be_set_to_any_level_regardless_of_validation_status():
    """
    Broader confirmation: every validation_status/confidence combination
    constructs successfully, including the semantically strangest ones
    (REJECTED+HIGH, CONFLICTED+HIGH) — proving this isn't narrowly about
    PROVISIONAL+HIGH, but that the two fields are fully uncoupled
    everywhere in the current model.
    """
    for validation_status in ValidationStatus:
        for confidence in ConfidenceLevel:
            uap = UAP(
                subject="test",
                information_class=InformationClass.FACT,
                validation_status=validation_status,
                result="test",
                source="test source",
                producer="test producer",
                confidence=confidence,
            )
            assert uap.validation_status == validation_status
            assert uap.confidence == confidence
