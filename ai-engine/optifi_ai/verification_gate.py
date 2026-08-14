"""
Verification Gate — Phase E6 brief: "Material personalised recommendations
must pass the independent verification layer. CIO cannot override REJECT.
Define clear handling for: PASS; PASS WITH CAUTION; REVISE; INSUFFICIENT
EVIDENCE; REJECT."

`verification-engine`'s actual, tested `VerdictType` has four values
(`PASS`, `PASS WITH CAUTION`, `FLAG`, `REJECT`; `FLAG` sub-typed by
`flagged_status` in {CONFLICTED, STALE, INCOMPLETE} — see
`optifi_verification.verdict.Verdict`). Rather than adding `REVISE` and
`INSUFFICIENT EVIDENCE` as new verdict values inside verification-engine
itself — a change to an already-implemented, independently-tested engine,
which CLAUDE.md says not to make without it being explicitly authorised —
this module maps the existing taxonomy onto the CIO's five response
categories:

    PASS                          -> PASS
    PASS WITH CAUTION             -> PASS_WITH_CAUTION
    FLAG (CONFLICTED or STALE)    -> REVISE               (recalculation is meaningful)
    FLAG (INCOMPLETE)             -> INSUFFICIENT_EVIDENCE
    REJECT                        -> REJECT

Per VERIFICATION_FRAMEWORK.md Section 8: "the CIO must omit a REJECTed
output from its synthesis entirely, unless an explicit override exists —
and if one does, the override itself must be logged and auditable, not a
silent bypass." Section 9, item 2 leaves *who* governs that override
mechanism undecided. Rather than inventing governance for an explicitly
open question, this module implements no override path at all: a REJECT
verdict always excludes its candidate here, full stop.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from optifi_verification import Verdict, VerdictType
from optifi_shared import ValidationStatus


class CIOVerdictHandling(str, Enum):
    PASS = "PASS"
    PASS_WITH_CAUTION = "PASS_WITH_CAUTION"
    REVISE = "REVISE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REJECT = "REJECT"


# Worst-first, mirroring shared/optifi_shared/validation_propagation.py's
# worst_validation_status convention: when several verdicts apply to the
# same candidate, the CIO's overall handling is the single worst one, not
# an average or a majority vote — a candidate is only as trustworthy as
# its weakest independent check.
_SEVERITY_ORDER = (
    CIOVerdictHandling.REJECT,
    CIOVerdictHandling.INSUFFICIENT_EVIDENCE,
    CIOVerdictHandling.REVISE,
    CIOVerdictHandling.PASS_WITH_CAUTION,
    CIOVerdictHandling.PASS,
)


def map_verdict_to_handling(verdict: Verdict) -> CIOVerdictHandling:
    if verdict.verdict_type == VerdictType.PASS:
        return CIOVerdictHandling.PASS
    if verdict.verdict_type == VerdictType.PASS_WITH_CAUTION:
        return CIOVerdictHandling.PASS_WITH_CAUTION
    if verdict.verdict_type == VerdictType.REJECT:
        return CIOVerdictHandling.REJECT

    # FLAG — Verdict's own validator already guarantees flagged_status is
    # one of CONFLICTED/STALE/INCOMPLETE here.
    if verdict.flagged_status in (ValidationStatus.CONFLICTED, ValidationStatus.STALE):
        return CIOVerdictHandling.REVISE
    return CIOVerdictHandling.INSUFFICIENT_EVIDENCE


@dataclass(frozen=True)
class GateResult:
    handling: CIOVerdictHandling
    excluded: bool  # True: this candidate must not appear in CIO synthesis at all
    reasons: list[str]


def apply_gate(verdicts: list[Verdict]) -> GateResult:
    """`verdicts` are every independent check that applies to one
    candidate (Stage 11 may run several — e.g. a loss-cap check plus a
    look-ahead check). Returns the single worst handling across all of
    them, per `_SEVERITY_ORDER`; `excluded=True` only for REJECT — the
    one verdict this phase treats as truly non-negotiable (Section 8, and
    module docstring above)."""
    if not verdicts:
        raise ValueError(
            "apply_gate: no verdicts supplied. A candidate that was never "
            "independently checked must not be treated as having passed — "
            "call this with at least one real Verdict."
        )

    handlings = [map_verdict_to_handling(v) for v in verdicts]
    worst = min(handlings, key=_SEVERITY_ORDER.index)
    reasons = [reason for verdict in verdicts for reason in verdict.reasons]
    return GateResult(handling=worst, excluded=(worst == CIOVerdictHandling.REJECT), reasons=reasons)
