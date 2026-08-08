"""
Tests for check_provenance_resolvable (VERIFICATION_FRAMEWORK.md,
Section 7; resolving ANALYTICAL_CONTRACT_SPEC.md Section 9, item 4).
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_verification import VerdictType, check_provenance_resolvable


def _make_uap(uap_id: str, provenance_chain: list[str] | None = None) -> UAP:
    return UAP(
        id=uap_id,
        subject="test subject",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result="test result",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
        provenance_chain=provenance_chain or [],
    )


def test_resolvable_and_acyclic_chain_passes():
    fact_a = _make_uap("fact-a")
    fact_b = _make_uap("fact-b")
    judgement = _make_uap("judgement-1", provenance_chain=["fact-a", "fact-b"])
    known_packets = {"fact-a": fact_a, "fact-b": fact_b, "judgement-1": judgement}

    verdict = check_provenance_resolvable(judgement, known_packets)

    assert verdict.verdict_type == VerdictType.PASS


def test_unresolvable_reference_rejects():
    judgement = _make_uap("judgement-1", provenance_chain=["nonexistent-id"])
    known_packets = {"judgement-1": judgement}

    verdict = check_provenance_resolvable(judgement, known_packets)

    assert verdict.verdict_type == VerdictType.REJECT
    assert any("unresolvable" in reason for reason in verdict.reasons)


def test_circular_reference_rejects():
    # judgement-1 -> estimate-1 -> judgement-1 (cycle)
    judgement = _make_uap("judgement-1", provenance_chain=["estimate-1"])
    estimate = _make_uap("estimate-1", provenance_chain=["judgement-1"])
    known_packets = {"judgement-1": judgement, "estimate-1": estimate}

    verdict = check_provenance_resolvable(judgement, known_packets)

    assert verdict.verdict_type == VerdictType.REJECT
    assert any("circular" in reason for reason in verdict.reasons)


def test_empty_provenance_chain_passes():
    fact = _make_uap("fact-a", provenance_chain=[])
    verdict = check_provenance_resolvable(fact, {"fact-a": fact})
    assert verdict.verdict_type == VerdictType.PASS
