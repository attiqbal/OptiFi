"""
check_provenance_resolvable — VERIFICATION_FRAMEWORK.md Section 7,
resolving ANALYTICAL_CONTRACT_SPEC.md Section 9, item 4: who validates
that `provenance_chain` references are non-circular and actually
resolvable? verification-engine, consistent with its auditability role
(VERIFICATION_FRAMEWORK.md Section 5.6).

Checks two things against a supplied set of known packets:
1. Resolvable — every id in `uap.provenance_chain` exists among the
   known packets.
2. Non-circular — following `provenance_chain` transitively never loops
   back to `uap`'s own id.
"""

from __future__ import annotations

from optifi_shared import UAP, ValidationStatus

from .verdict import FailureCategory, Verdict, VerdictType


def check_provenance_resolvable(uap: UAP, known_packets: dict[str, UAP]) -> Verdict:
    """
    `known_packets` maps packet id -> UAP, standing in for whatever
    packet store eventually exists — this function only needs lookup
    access, not a real persistence layer.
    """
    missing = [pid for pid in uap.provenance_chain if pid not in known_packets]
    if missing:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=[
                f"provenance_chain references unresolvable packet id(s): {missing}"
            ],
            failure_category=FailureCategory.UNVERIFIABLE_PROVENANCE,
        )

    def _reaches_root(current_id: str, visited: frozenset[str]) -> bool:
        if current_id == uap.id:
            return True
        if current_id in visited:
            return False  # already-explored branch, not a path back to the root
        packet = known_packets.get(current_id)
        if packet is None:
            return False
        next_visited = visited | {current_id}
        return any(_reaches_root(next_id, next_visited) for next_id in packet.provenance_chain)

    circular = [pid for pid in uap.provenance_chain if _reaches_root(pid, frozenset())]
    if circular:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=[
                "provenance_chain contains a circular reference back to "
                f"this packet's own id, via: {circular}"
            ],
            failure_category=FailureCategory.UNVERIFIABLE_PROVENANCE,
        )

    # Structurally the same gap as audit_corroboration's: resolvable and
    # acyclic only confirms the chain can be TRACED, not that what it
    # traces to is itself settled. VERIFICATION_FRAMEWORK.md Section 4's
    # own PASS WITH CAUTION example -- "a dependency was itself only
    # PROVISIONAL" -- applies directly to a directly-referenced upstream
    # packet that isn't VERIFIED. Not FLAG: nothing here contradicts
    # another output, and the chain itself is genuinely fine (resolvable,
    # acyclic) -- it's the upstream packet's OWN status that isn't
    # settled, exactly the PASS WITH CAUTION shape, not a newly-found
    # inconsistency.
    non_verified_upstream = [
        (pid, known_packets[pid].validation_status.value)
        for pid in uap.provenance_chain
        if known_packets[pid].validation_status != ValidationStatus.VERIFIED
    ]
    if non_verified_upstream:
        return Verdict(
            verdict_type=VerdictType.PASS_WITH_CAUTION,
            reasons=[
                "provenance_chain is fully resolvable and acyclic, but "
                "references upstream packet(s) that are not themselves "
                f"VERIFIED: {non_verified_upstream}"
            ],
        )

    return Verdict(
        verdict_type=VerdictType.PASS,
        reasons=["provenance_chain is fully resolvable and acyclic"],
    )
