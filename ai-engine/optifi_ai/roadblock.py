"""
Roadblock Management — Phase E6 brief:
"If required information is unavailable: CIO should identify missing
dependency; request refresh/fallback if approved; qualify or defer the
conclusion. Never hallucinate around the problem."

This module only *detects* roadblocks — missing specialist output, or
data older than a caller-supplied freshness bound. It never invents a
substitute value and it never silently proceeds past one; `orchestrator.py`
is the caller that decides how to qualify/defer once a roadblock is found.

No "request refresh" is implemented: `data-engine` has no live vendor
connected (README.md, "Experimental / not yet connected"), so there is
nothing this phase could genuinely refresh. A roadblock can only be
surfaced, never silently resolved by fetching something newer.

`check_staleness` deliberately takes `max_age` as a required parameter
with no default. VERIFICATION_FRAMEWORK.md Section 9, item 1 explicitly
leaves staleness thresholds uncalibrated ("deliberately not fixed —
calibration against real use is a later step"); hardcoding a number here
would silently resolve that open question rather than carry it forward.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from optifi_shared import UAP

from .intent import SpecialistEngine


@dataclass(frozen=True)
class Roadblock:
    kind: str  # "MISSING_DEPENDENCY" | "STALE_DATA"
    description: str
    subject: str | None = None


def detect_missing_dependencies(
    required: frozenset[SpecialistEngine], available: frozenset[SpecialistEngine]
) -> list[Roadblock]:
    """`required` comes from `intent.classify_required_engines`; `available`
    is whichever engines actually have output present in the caller's
    pool. Anything in `required` but not `available` is a roadblock —
    never silently dropped from the routing decision."""
    missing = sorted(required - available, key=lambda e: e.value)
    return [
        Roadblock(
            kind="MISSING_DEPENDENCY",
            description=f"{engine.value} output was required by routing but is not available",
            subject=engine.value,
        )
        for engine in missing
    ]


def check_staleness(uaps: list[UAP], now: datetime, max_age: timedelta) -> list[Roadblock]:
    """Checked against present time (`now`), per VERIFICATION_FRAMEWORK.md
    Section 5.2's "present-time freshness" — never against whatever the
    producing engine itself asserted. A UAP with no time field set at all
    cannot be checked and is not assumed fresh or stale; see
    `evidence_as_of`/`observation_time`/`generated_at` fallback order
    below, matching `UAP`'s own field semantics (shared/optifi_shared/uap.py)."""
    roadblocks = []
    for uap in uaps:
        reference_time = uap.evidence_as_of or uap.observation_time or uap.generated_at
        if reference_time is None:
            continue
        age = now - reference_time
        if age > max_age:
            roadblocks.append(
                Roadblock(
                    kind="STALE_DATA",
                    description=(
                        f"'{uap.subject}' is {age} old as of {now!r}, exceeding max_age={max_age}"
                    ),
                    subject=uap.subject,
                )
            )
    return roadblocks
