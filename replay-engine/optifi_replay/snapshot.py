"""
HistoricalSnapshot — PHASE E5 brief, Part 1: reconstruct exactly what
OptiFi could have known at a historical date T. "Anything published
after T must be inaccessible."

`build_snapshot` is the enforcement point: given every UAP that exists
ANYWHERE in today's stores (a superset — some genuinely available at T,
some published later, some revised later), it returns only the subset
that was genuinely knowable at T, with the correct historical vintage
and validation status for that moment — not today's.

Two things make this more than a simple timestamp filter:

1. **Vintage resolution.** A subject with multiple UAPs linked via
   `supersede()` (`shared/optifi_shared/uap.py`) represents successive
   releases of the same underlying fact (e.g. a CPI advance estimate
   later revised). The vintage "current" at T is whichever one was
   genuinely available at T and not yet superseded BY T — not
   necessarily today's latest vintage.
2. **Historical status reconstruction.** A vintage that today's live
   store marks `validation_status=SUPERSEDED` (because a LATER revision
   has since superseded it) must be reported in whatever status it
   actually held AT TIME T if that later revision was not yet available
   then — from OptiFi's own historical perspective, the superseding
   event hadn't happened yet. Silently reporting today's SUPERSEDED
   status would itself be a (subtle) form of hindsight leakage: it
   reveals that "this was going to be revised," information only
   available in hindsight.

Availability itself reuses the exact "genuinely available" definition
`verification-engine`'s `check_no_look_ahead_contamination` already
established (Phase E1) — `max(publication_time, retrieval_time)` — a
small, local reimplementation rather than importing that module's
private helper, consistent with this project's existing precedent for
small utility functions (e.g. `ensemble.py`'s confidence-threshold
constants, aligned with but not imported from sibling code).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from optifi_evaluation import ModelScorecard
from optifi_shared import UAP, ValidationStatus


def _genuinely_available_time(uap: UAP) -> datetime | None:
    times = [t for t in (uap.publication_time, uap.retrieval_time) if t is not None]
    return max(times) if times else None


@dataclass(frozen=True)
class HistoricalSnapshot:
    as_of: datetime
    available_uaps: tuple[UAP, ...]
    excluded_future: tuple[UAP, ...]
    excluded_unverifiable: tuple[UAP, ...]
    excluded_superseded_by_t: tuple[UAP, ...]
    portfolio: dict[str, float] = field(default_factory=dict)
    mandate: dict = field(default_factory=dict)

    def by_subject(self, subject: str) -> UAP | None:
        matches = [u for u in self.available_uaps if u.subject == subject]
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError(
                f"HistoricalSnapshot.by_subject: {len(matches)} available UAPs "
                f"share subject {subject!r} after vintage resolution — this "
                "should not happen for a well-formed supersession chain; "
                "use available_uaps directly if multiple genuinely-competing "
                "(non-vintage) claims for this subject are expected."
            )
        return matches[0]

    def get(self, uap_id: str) -> UAP | None:
        for uap in self.available_uaps:
            if uap.id == uap_id:
                return uap
        return None


def build_snapshot(
    as_of: datetime,
    candidate_uaps: list[UAP],
    portfolio: dict[str, float] | None = None,
    mandate: dict | None = None,
) -> HistoricalSnapshot:
    """
    `candidate_uaps`: every UAP that exists anywhere, across every
    vintage/revision — a superset, deliberately, so this function's own
    filtering is what's actually being tested (a caller that only ever
    passes already-filtered input proves nothing about whether the
    filter itself works).
    """
    available_at_t: list[UAP] = []
    excluded_future: list[UAP] = []
    excluded_unverifiable: list[UAP] = []

    for uap in candidate_uaps:
        available_time = _genuinely_available_time(uap)
        if available_time is None:
            excluded_unverifiable.append(uap)
        elif available_time > as_of:
            excluded_future.append(uap)
        else:
            available_at_t.append(uap)

    # --- Vintage resolution + historical status reconstruction ---
    by_subject: dict[str, list[UAP]] = {}
    for uap in available_at_t:
        by_subject.setdefault(uap.subject, []).append(uap)

    resolved: list[UAP] = []
    excluded_superseded_by_t: list[UAP] = []
    for subject, uaps in by_subject.items():
        if len(uaps) == 1:
            resolved.append(_reconstruct_status(uaps[0], available_at_t))
            continue

        # More than one T-available UAP shares this subject: exclude any
        # that is superseded by ANOTHER T-available UAP for the same
        # subject — what remains is whichever vintage was current at T.
        superseded_ids = {
            old_id
            for uap in uaps
            for old_id in uap.supersedes
        }
        current_at_t = [u for u in uaps if u.id not in superseded_ids]
        for u in uaps:
            if u.id in superseded_ids:
                excluded_superseded_by_t.append(u)
        for u in current_at_t:
            resolved.append(_reconstruct_status(u, available_at_t))

    return HistoricalSnapshot(
        as_of=as_of,
        available_uaps=tuple(resolved),
        excluded_future=tuple(excluded_future),
        excluded_unverifiable=tuple(excluded_unverifiable),
        excluded_superseded_by_t=tuple(excluded_superseded_by_t),
        portfolio=portfolio or {},
        mandate=mandate or {},
    )


def filter_available_scorecards(as_of: datetime, candidate_scorecards: list[ModelScorecard]) -> list[ModelScorecard]:
    """
    Part 1's "model versions" bullet: a model scorecard evaluated AFTER
    T was not yet known at T — including it in a historical snapshot
    would let a replay silently benefit from performance information
    (or a model version) that didn't exist yet. `ModelScorecard` is not
    a `UAP` (it's `evaluation-engine`'s own dataclass, Phase E3) and has
    no `publication_time`/`retrieval_time` — its own `last_evaluation`
    field is the equivalent "when did this become known" timestamp.
    """
    return [s for s in candidate_scorecards if s.last_evaluation <= as_of]


def _reconstruct_status(uap: UAP, available_at_t: list[UAP]) -> UAP:
    """
    If `uap.validation_status` is SUPERSEDED, but nothing in
    `available_at_t` actually references it via `supersedes` (i.e. the
    revision that superseded it, in today's live store, was not itself
    available at T), the SUPERSEDED status is hindsight — reconstruct it
    to VERIFIED, the status it held before a still-future revision
    replaced it. Never mutates the input; returns a copy when
    reconstruction is needed, the same object otherwise.
    """
    if uap.validation_status != ValidationStatus.SUPERSEDED:
        return uap
    superseded_by_something_available_at_t = any(uap.id in other.supersedes for other in available_at_t)
    if superseded_by_something_available_at_t:
        return uap  # genuinely superseded by T too — today's status is correct at T as well
    return uap.model_copy(update={"validation_status": ValidationStatus.VERIFIED})
