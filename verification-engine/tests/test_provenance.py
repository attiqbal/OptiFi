"""
Tests for check_provenance_resolvable (VERIFICATION_FRAMEWORK.md,
Section 7; resolving ANALYTICAL_CONTRACT_SPEC.md Section 9, item 4).
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_verification import VerdictType, check_provenance_resolvable


def _make_uap(
    uap_id: str,
    provenance_chain: list[str] | None = None,
    validation_status: ValidationStatus = ValidationStatus.VERIFIED,
) -> UAP:
    return UAP(
        id=uap_id,
        subject="test subject",
        information_class=InformationClass.FACT,
        validation_status=validation_status,
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


def test_resolvable_acyclic_chain_with_non_verified_upstream_produces_pass_with_caution():
    """
    Verdict-gap fix, built from scratch (no prior fixture came close to
    this): a genuinely resolvable, acyclic chain -- exactly like
    test_resolvable_and_acyclic_chain_passes above -- except one upstream
    packet is PROVISIONAL rather than VERIFIED. Resolvability and
    acyclicity alone only confirm the chain can be TRACED, not that what
    it traces to is itself settled -- VERIFICATION_FRAMEWORK.md Section
    4's own PASS WITH CAUTION example ("a dependency was itself only
    PROVISIONAL") applies directly. The specific non-VERIFIED packet's id
    and status must be named, not just a generic caveat.
    """
    provisional_fact = _make_uap("fact-a", validation_status=ValidationStatus.PROVISIONAL)
    verified_fact = _make_uap("fact-b")
    judgement = _make_uap("judgement-1", provenance_chain=["fact-a", "fact-b"])
    known_packets = {"fact-a": provisional_fact, "fact-b": verified_fact, "judgement-1": judgement}

    verdict = check_provenance_resolvable(judgement, known_packets)

    assert verdict.verdict_type == VerdictType.PASS_WITH_CAUTION
    reasons_joined = " ".join(verdict.reasons)
    assert "fact-a" in reasons_joined
    assert "PROVISIONAL" in reasons_joined
    # The already-VERIFIED "fact-b" must not be named as a concern.
    assert "fact-b" not in reasons_joined


def test_resolvable_acyclic_chain_where_every_upstream_is_verified_still_passes_cleanly():
    """Control case: confirms the fix didn't break the ordinary all-VERIFIED path."""
    fact_a = _make_uap("fact-a")
    fact_b = _make_uap("fact-b")
    judgement = _make_uap("judgement-1", provenance_chain=["fact-a", "fact-b"])
    known_packets = {"fact-a": fact_a, "fact-b": fact_b, "judgement-1": judgement}

    verdict = check_provenance_resolvable(judgement, known_packets)

    assert verdict.verdict_type == VerdictType.PASS
