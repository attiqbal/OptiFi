"""
audit_corroboration — an independent re-derivation of
ANALYTICAL_CONTRACT_SPEC.md Section 4a's corroboration logic, checking
whether a fact's claimed VERIFIED status is actually justified.

Deliberately does NOT call data-engine's `corroborate_fact` — this exists
to catch a case where a fact somehow got marked VERIFIED without
genuinely satisfying Section 4a's rules (independent corroboration or a
structured cross-check), which calling the same function that produced
the claim in the first place could never detect.
"""

from __future__ import annotations

from optifi_shared import InformationClass, UAP, ValidationStatus

from .verdict import FailureCategory, Verdict, VerdictType


def audit_corroboration(verified_fact: UAP, sources_used: list[UAP]) -> Verdict:
    """
    Independently check whether `sources_used` actually justifies
    `verified_fact`'s claimed VERIFIED status, per
    ANALYTICAL_CONTRACT_SPEC.md Section 4a: either (a) at least one
    genuinely independent source (a `source` value differing from
    `verified_fact`'s own, and from every other candidate already
    counted — no double-counting shared-origin repeats), or (b) at least
    one structured cross-check (a candidate that is itself
    `information_class=FACT`, `validation_status=VERIFIED`).

    Raises ValueError if `verified_fact` is not itself
    `information_class=FACT`, `validation_status=VERIFIED` — this audit
    only makes sense for something already claiming that status.
    """
    if (
        verified_fact.information_class != InformationClass.FACT
        or verified_fact.validation_status != ValidationStatus.VERIFIED
    ):
        raise ValueError(
            "audit_corroboration: verified_fact must have "
            "information_class=FACT and validation_status=VERIFIED — "
            "this audit only makes sense for something already claiming "
            f"VERIFIED status; got information_class="
            f"{verified_fact.information_class!r}, validation_status="
            f"{verified_fact.validation_status!r}."
        )

    # A structured cross-check is BY DEFINITION already FACT+VERIFIED
    # (that's the criterion itself), so it never needs a caution.
    structured_cross_check_found = any(
        source.information_class == InformationClass.FACT
        and source.validation_status == ValidationStatus.VERIFIED
        for source in sources_used
    )

    seen_sources: set[str] = {verified_fact.source}
    independent_sources: list[UAP] = []
    for source in sources_used:
        if source.source not in seen_sources:
            seen_sources.add(source.source)
            independent_sources.append(source)

    if structured_cross_check_found or any(
        source.validation_status == ValidationStatus.VERIFIED for source in independent_sources
    ):
        return Verdict(
            verdict_type=VerdictType.PASS,
            reasons=[
                "independent re-derivation confirms the claimed VERIFIED "
                "status is justified"
            ],
        )

    if independent_sources:
        # VERIFICATION_FRAMEWORK.md Section 4's own literal example of
        # PASS WITH CAUTION: "output stands, but a caveat is attached
        # (e.g. a dependency was itself only PROVISIONAL)." The
        # independence criterion (Section 4a, (a)) is genuinely
        # satisfied here -- the confirming source(s) really are of a
        # different origin -- but none of them has itself reached
        # VERIFIED yet, so the corroboration this claim rests on is
        # itself not fully settled. Not FLAG: nothing here contradicts
        # another output, is stale, or is missing -- corroboration WAS
        # found, it just isn't fully confirmed yet.
        non_verified_statuses = sorted(
            {source.validation_status.value for source in independent_sources}
        )
        return Verdict(
            verdict_type=VerdictType.PASS_WITH_CAUTION,
            reasons=[
                "independent re-derivation confirms a genuinely "
                "independent source exists, but the confirming source(s) "
                "are not themselves VERIFIED yet (validation_status: "
                f"{non_verified_statuses}) -- the claimed VERIFIED status "
                "stands, but is only as settled as its own least-settled "
                "corroborating source"
            ],
        )

    return Verdict(
        verdict_type=VerdictType.REJECT,
        reasons=[
            "claimed VERIFIED status is not justified: sources_used "
            "contains no source genuinely independent of the fact's own "
            "source, and no structured cross-check (an already-VERIFIED "
            "FACT) is present among sources_used"
        ],
        failure_category=FailureCategory.DATA_QUALITY,
    )
