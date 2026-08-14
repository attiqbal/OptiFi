from optifi_ai.evidence_trace import trace_evidence
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus


def _uap(subject: str, **overrides) -> UAP:
    defaults = dict(
        subject=subject,
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=1.0,
        source="test",
        producer="test",
        confidence=ConfidenceLevel.MODERATE,
    )
    defaults.update(overrides)
    return UAP(**defaults)


def test_traces_back_to_root_fact_through_multiple_hops():
    root = _uap("root fact")
    middle = _uap("middle estimate", dependencies=[root.id])
    top = _uap("top judgement", dependencies=[middle.id])

    known = {root.id: root, middle.id: middle}
    reachable = trace_evidence(top, known)

    reachable_ids = {u.id for u in reachable}
    assert top.id in reachable_ids
    assert middle.id in reachable_ids
    assert root.id in reachable_ids


def test_leaf_uap_traces_to_itself_only():
    leaf = _uap("a true leaf")
    reachable = trace_evidence(leaf)
    assert [u.id for u in reachable] == [leaf.id]


def test_unresolved_reference_does_not_crash_and_is_simply_absent():
    orphan = _uap("references something unknown", dependencies=["does-not-exist"])
    reachable = trace_evidence(orphan, known_uaps={})
    assert [u.id for u in reachable] == [orphan.id]
