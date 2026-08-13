"""
Validation-status propagation — Phase E1 hardening.

ANALYTICAL_CONTRACT_SPEC.md Section 8: "If a dependency an engine relied
on failed or degraded, that must be visible in this packet's own
validation_status, not silently absorbed by falling back to a default."
This module gives that principle a concrete, reusable mechanism: a
downstream engine's own intended `validation_status` may be DOWNGRADED
by a worse upstream status, but this utility never upgrades — upgrading
(e.g. `PROVISIONAL` -> `VERIFIED`) only ever happens through the
explicit, approved mechanisms this project already has
(`corroborate_fact`, ANALYTICAL_CONTRACT_SPEC.md Section 4a;
`apply_verdict`'s PASS branch, VERIFICATION_FRAMEWORK.md Section 4) —
never as a side effect of this utility.

Adopting this utility at any given call site is NOT mandated by this
module — it is available, tested infrastructure a downstream engine CAN
use to compute its own `validation_status` honestly from its
dependencies' statuses. Migrating every existing engine function to call
it is a separate, later piece of work (see the Phase E1 deliverable's
migration notes), not something this module forces silently.
"""

from __future__ import annotations

from .uap import UAP, ValidationStatus

# Severity ranking, worst (most severe, rank 0) to best (least severe) —
# a genuine design choice, not something ANALYTICAL_CONTRACT_SPEC.md
# itself defines as a strict linear order across all seven values:
#
# REJECTED: failed validation outright — most severe by definition
#   (ANALYTICAL_CONTRACT_SPEC.md Section 4: "must not be used downstream
#   without an explicit, logged override").
# CONFLICTED: active, unresolved disagreement between sources/models —
#   ranked above STALE/INCOMPLETE because it represents a genuine,
#   currently-live inconsistency, not merely missing or ageing
#   information.
# STALE / INCOMPLETE: ranked equal to each other — both represent a
#   genuine, unresolved gap (one temporal, one structural), with no
#   principled reason established here to prefer one over the other.
# PROVISIONAL: not yet corroborated, but not flagged as actively wrong,
#   missing, or conflicting — the mildest of the "not fully trusted"
#   statuses.
# SUPERSEDED / VERIFIED: both treated as "settled, no propagation
#   concern" for this utility's purposes. SUPERSEDED
#   (ANALYTICAL_CONTRACT_SPEC.md Section 4) "was valid, and possibly
#   VERIFIED, at the time" and was replaced through the same explicit,
#   approved process (`supersede()`) that VERIFIED itself requires
#   (corroboration/verification) — it is not an unresolved QUALITY issue
#   in the sense this utility exists to catch, only an old vintage.
#   Whether depending on a superseded (rather than current) vintage
#   deserves its own, separate signal is a genuinely different concern
#   from validation_status propagation, and is not addressed by this
#   module — see the Phase E1 deliverable's open questions.
_SEVERITY_RANK: dict[ValidationStatus, int] = {
    ValidationStatus.REJECTED: 0,
    ValidationStatus.CONFLICTED: 1,
    ValidationStatus.STALE: 2,
    ValidationStatus.INCOMPLETE: 2,
    ValidationStatus.PROVISIONAL: 3,
    ValidationStatus.SUPERSEDED: 4,
    ValidationStatus.VERIFIED: 4,
}


def worst_validation_status(statuses: list[ValidationStatus]) -> ValidationStatus | None:
    """The most severe status among `statuses`, per the ranking above.
    Returns `None` for an empty list — there is nothing to compare, not
    an implicit VERIFIED."""
    if not statuses:
        return None
    return min(statuses, key=lambda status: _SEVERITY_RANK[status])


def propagate_validation_status(
    own_intended_status: ValidationStatus, upstream: list[UAP]
) -> ValidationStatus:
    """
    Returns `own_intended_status`, DOWNGRADED to the worst status found
    among `upstream`'s own `validation_status` values if that is more
    severe than `own_intended_status` — never upgraded. A downstream
    engine calls this with the status it would otherwise have assigned
    its own output, and the actual upstream UAPs its result depends on;
    the returned value is what it should actually use.

    An engine may still choose to be MORE conservative than this
    function's result on its own judgement (e.g. treating any
    non-VERIFIED upstream as INCOMPLETE regardless of severity ranking)
    — this function establishes a floor (never silently better than the
    worst upstream input), not a ceiling.
    """
    worst_upstream = worst_validation_status([u.validation_status for u in upstream])
    if worst_upstream is None:
        return own_intended_status
    if _SEVERITY_RANK[worst_upstream] < _SEVERITY_RANK[own_intended_status]:
        return worst_upstream
    return own_intended_status
