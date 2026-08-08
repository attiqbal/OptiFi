"""
apply_verdict — mapping a Verdict onto a UAP's validation_status,
per VERIFICATION_FRAMEWORK.md Section 4:

- PASS: validation_status may move toward VERIFIED.
- PASS WITH CAUTION: validation_status unchanged, but the caution note
  must be visible downstream — recorded here in the returned UAP's
  `limitations`.
- FLAG: validation_status becomes CONFLICTED, STALE, or INCOMPLETE, as
  specified by the verdict's own `flagged_status`.
- REJECT: validation_status becomes REJECTED.

Never mutates the input UAP — always returns a new one.
"""

from __future__ import annotations

from optifi_shared import UAP, ValidationStatus

from .verdict import Verdict, VerdictType


def apply_verdict(uap: UAP, verdict: Verdict) -> UAP:
    """Apply `verdict`'s effect to `uap`, returning a new UAP (no mutation)."""
    if verdict.verdict_type == VerdictType.PASS:
        return uap.model_copy(
            deep=True, update={"validation_status": ValidationStatus.VERIFIED}
        )

    if verdict.verdict_type == VerdictType.PASS_WITH_CAUTION:
        caution_notes = [f"verification caution: {reason}" for reason in verdict.reasons]
        return uap.model_copy(
            deep=True,
            update={"limitations": [*uap.limitations, *caution_notes]},
        )

    if verdict.verdict_type == VerdictType.FLAG:
        # Verdict's own validator already guarantees flagged_status is one
        # of CONFLICTED/STALE/INCOMPLETE for a FLAG verdict.
        return uap.model_copy(
            deep=True, update={"validation_status": verdict.flagged_status}
        )

    # REJECT
    return uap.model_copy(
        deep=True, update={"validation_status": ValidationStatus.REJECTED}
    )
