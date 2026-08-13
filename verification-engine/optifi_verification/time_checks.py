"""
check_no_look_ahead_contamination — Phase E1 hardening.

Independently verifies a packet's time-semantics invariant: a packet
with `as_of=T` must never legally depend on an upstream record that
wasn't genuinely available by `T`. Mirrors `check_provenance_resolvable`'s
pattern exactly (same `known_packets` id->UAP lookup convention, same
independence principle — this never trusts a producing engine's own
claim that its inputs were contemporaneous) and lives alongside it for
the same reason: this is another auditability check
(VERIFICATION_FRAMEWORK.md Section 5.6), not a corroboration or
optimisation-candidate concern.

"Genuinely available" for an upstream packet is `max(publication_time,
retrieval_time)` when both are present -- a record isn't actually usable
by OptiFi before OptiFi retrieved it, even if the source published it
earlier; whichever of the two is present alone is used; if neither is
present, that specific reference cannot be time-checked at all (not
assumed safe -- see the PASS WITH CAUTION path below, mirroring how an
unresolved provenance reference is disclosed rather than silently
ignored, VERIFICATION_FRAMEWORK.md Section 4's PASS WITH CAUTION shape).

`as_of` is a new, optional field (Phase E1) that most existing packets
do not set -- a packet with no `as_of` claims no cutoff, so there is
nothing to check, and this function passes trivially rather than
penalising every pre-existing packet for a field that didn't exist when
it was produced.
"""

from __future__ import annotations

from datetime import datetime

from optifi_shared import UAP

from .verdict import FailureCategory, Verdict, VerdictType


def _genuinely_available_time(upstream: UAP) -> datetime | None:
    times = [t for t in (upstream.publication_time, upstream.retrieval_time) if t is not None]
    return max(times) if times else None


def check_no_look_ahead_contamination(uap: UAP, known_packets: dict[str, UAP]) -> Verdict:
    """
    `known_packets` maps packet id -> UAP, the same convention
    `check_provenance_resolvable` uses. Checks every id referenced in
    BOTH `uap.dependencies` and `uap.provenance_chain` (deduplicated) --
    look-ahead contamination could enter via either.
    """
    if uap.as_of is None:
        return Verdict(
            verdict_type=VerdictType.PASS,
            reasons=[
                "no as_of cutoff set on this packet; nothing to check for "
                "look-ahead contamination"
            ],
        )

    referenced_ids = sorted({*uap.dependencies, *uap.provenance_chain})
    if not referenced_ids:
        return Verdict(
            verdict_type=VerdictType.PASS,
            reasons=["no dependencies or provenance_chain references; nothing to check"],
        )

    violations: list[str] = []
    unverifiable: list[str] = []
    for ref_id in referenced_ids:
        upstream = known_packets.get(ref_id)
        if upstream is None:
            unverifiable.append(f"'{ref_id}' (unresolved — cannot be time-checked)")
            continue
        available_time = _genuinely_available_time(upstream)
        if available_time is None:
            unverifiable.append(
                f"'{ref_id}' (no publication_time/retrieval_time set — cannot be time-checked)"
            )
            continue
        if available_time > uap.as_of:
            violations.append(
                f"'{ref_id}' was not genuinely available until "
                f"{available_time!r}, after this packet's own as_of "
                f"cutoff ({uap.as_of!r})"
            )

    if violations:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=[
                "look-ahead contamination: this packet depends on "
                "upstream record(s) that were not genuinely available "
                f"at its own as_of cutoff: {'; '.join(violations)}"
            ],
            failure_category=FailureCategory.DATA_QUALITY,
        )

    if unverifiable:
        # Genuine borderline case, same shape as this session's other
        # PASS WITH CAUTION verdicts: the check cannot RULE OUT
        # contamination for these specific references, so it must not
        # report a clean, uncaveated PASS.
        return Verdict(
            verdict_type=VerdictType.PASS_WITH_CAUTION,
            reasons=[
                "as_of respected for every upstream reference with a "
                "known availability time, but "
                f"{len(unverifiable)} reference(s) could not be "
                f"time-checked: {'; '.join(unverifiable)}"
            ],
        )

    return Verdict(
        verdict_type=VerdictType.PASS,
        reasons=[
            "every resolvable upstream reference was genuinely available "
            "at or before this packet's own as_of cutoff"
        ],
    )
