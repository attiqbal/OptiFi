"""
Tests for check_no_look_ahead_contamination (Phase E1 hardening).
"""

from datetime import datetime, timedelta, timezone

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_verification import VerdictType, check_no_look_ahead_contamination

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_uap(
    uap_id: str,
    dependencies: list[str] | None = None,
    provenance_chain: list[str] | None = None,
    as_of: datetime | None = None,
    publication_time: datetime | None = None,
    retrieval_time: datetime | None = None,
) -> UAP:
    return UAP(
        id=uap_id,
        subject="test subject",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result="test result",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=dependencies or [],
        provenance_chain=provenance_chain or [],
        as_of=as_of,
        publication_time=publication_time,
        retrieval_time=retrieval_time,
    )


def test_no_as_of_set_passes_trivially():
    """A packet claiming no cutoff at all has nothing to check against —
    and every pre-existing packet in this codebase (produced before this
    field existed) falls into this case."""
    fact = _make_uap("fact-a", provenance_chain=["upstream-a"])
    upstream = _make_uap("upstream-a", publication_time=T0 + timedelta(days=10))
    verdict = check_no_look_ahead_contamination(fact, {"fact-a": fact, "upstream-a": upstream})
    assert verdict.verdict_type == VerdictType.PASS


def test_no_dependencies_or_provenance_chain_passes():
    fact = _make_uap("fact-a", as_of=T0)
    verdict = check_no_look_ahead_contamination(fact, {"fact-a": fact})
    assert verdict.verdict_type == VerdictType.PASS


def test_upstream_available_before_as_of_passes():
    fact = _make_uap("fact-a", provenance_chain=["upstream-a"], as_of=T0)
    upstream = _make_uap("upstream-a", publication_time=T0 - timedelta(days=1))
    verdict = check_no_look_ahead_contamination(fact, {"fact-a": fact, "upstream-a": upstream})
    assert verdict.verdict_type == VerdictType.PASS


def test_upstream_available_exactly_at_as_of_passes():
    fact = _make_uap("fact-a", provenance_chain=["upstream-a"], as_of=T0)
    upstream = _make_uap("upstream-a", publication_time=T0)
    verdict = check_no_look_ahead_contamination(fact, {"fact-a": fact, "upstream-a": upstream})
    assert verdict.verdict_type == VerdictType.PASS


def test_future_information_violates_as_of_and_is_rejected():
    """
    Test category #4 (required): a packet depending on an upstream
    record only published/retrieved AFTER its own as_of cutoff must be
    rejected, naming the specific offending reference and both times.
    """
    fact = _make_uap("fact-a", provenance_chain=["upstream-a"], as_of=T0)
    future_upstream = _make_uap("upstream-a", publication_time=T0 + timedelta(days=1))
    verdict = check_no_look_ahead_contamination(
        fact, {"fact-a": fact, "upstream-a": future_upstream}
    )
    assert verdict.verdict_type == VerdictType.REJECT
    reasons_joined = " ".join(verdict.reasons)
    assert "upstream-a" in reasons_joined
    assert "look-ahead contamination" in reasons_joined


def test_retrieval_time_after_publication_time_is_the_binding_constraint():
    """
    A record published before as_of but not actually RETRIEVED by
    OptiFi until after as_of is still look-ahead contamination — it
    wasn't genuinely available to OptiFi at as_of, regardless of when
    the source itself released it.
    """
    fact = _make_uap("fact-a", provenance_chain=["upstream-a"], as_of=T0)
    upstream = _make_uap(
        "upstream-a",
        publication_time=T0 - timedelta(days=5),  # published before as_of
        retrieval_time=T0 + timedelta(hours=1),  # but only retrieved after
    )
    verdict = check_no_look_ahead_contamination(fact, {"fact-a": fact, "upstream-a": upstream})
    assert verdict.verdict_type == VerdictType.REJECT


def test_multiple_dependency_and_provenance_references_are_deduplicated_and_all_checked():
    fact = _make_uap(
        "fact-a",
        dependencies=["upstream-a", "upstream-b"],
        provenance_chain=["upstream-a"],  # same id as a dependency too
        as_of=T0,
    )
    upstream_a = _make_uap("upstream-a", publication_time=T0 - timedelta(days=1))
    future_upstream_b = _make_uap("upstream-b", publication_time=T0 + timedelta(days=1))
    verdict = check_no_look_ahead_contamination(
        fact, {"fact-a": fact, "upstream-a": upstream_a, "upstream-b": future_upstream_b}
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert "upstream-b" in " ".join(verdict.reasons)
    assert "upstream-a" not in " ".join(verdict.reasons)


def test_upstream_with_no_time_fields_produces_pass_with_caution_not_a_silent_pass():
    """
    An upstream reference that resolves but carries no
    publication_time/retrieval_time genuinely cannot be time-checked —
    this must not be silently treated as safe.
    """
    fact = _make_uap("fact-a", provenance_chain=["upstream-a"], as_of=T0)
    untimed_upstream = _make_uap("upstream-a")  # no publication_time/retrieval_time
    verdict = check_no_look_ahead_contamination(
        fact, {"fact-a": fact, "upstream-a": untimed_upstream}
    )
    assert verdict.verdict_type == VerdictType.PASS_WITH_CAUTION
    assert "upstream-a" in " ".join(verdict.reasons)


def test_unresolvable_reference_also_produces_pass_with_caution():
    fact = _make_uap("fact-a", provenance_chain=["nonexistent-id"], as_of=T0)
    verdict = check_no_look_ahead_contamination(fact, {"fact-a": fact})
    assert verdict.verdict_type == VerdictType.PASS_WITH_CAUTION
    assert "nonexistent-id" in " ".join(verdict.reasons)


def test_violation_takes_priority_over_unverifiable_reference():
    """If at least one dependency IS a genuine violation, that's a REJECT
    even if another dependency is merely unverifiable — a known problem
    must not be diluted into a mere caution by an unrelated unknown."""
    fact = _make_uap(
        "fact-a",
        provenance_chain=["future-upstream", "untimed-upstream"],
        as_of=T0,
    )
    future_upstream = _make_uap("future-upstream", publication_time=T0 + timedelta(days=1))
    untimed_upstream = _make_uap("untimed-upstream")
    verdict = check_no_look_ahead_contamination(
        fact,
        {"fact-a": fact, "future-upstream": future_upstream, "untimed-upstream": untimed_upstream},
    )
    assert verdict.verdict_type == VerdictType.REJECT
