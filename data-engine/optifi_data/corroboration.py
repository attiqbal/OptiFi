"""
The corroboration mechanism — ANALYTICAL_CONTRACT_SPEC.md, Section 4a.

Pure logic operating on UAP objects: a `PROVISIONAL` fact becomes
`VERIFIED` only through independent corroboration or a structured
cross-check, never through elapsed time or repetition of the same
underlying source. This module implements exactly that decision — no
real or mock external data source is implemented or connected here; the
candidate corroborating UAPs are supplied directly by the caller, exactly
as they would be by whatever future Stage 1/2 data-acquisition process
produces them.
"""

from __future__ import annotations

from optifi_shared import InformationClass, UAP, ValidationStatus


def corroborate_fact(provisional_fact: UAP, candidate_sources: list[UAP]) -> UAP:
    """
    Attempt to corroborate `provisional_fact` (ANALYTICAL_CONTRACT_SPEC.md
    Section 4a) against `candidate_sources`, via either mechanism:

    1. Structured cross-check — any candidate that is itself an already-
       `VERIFIED` `FACT` is sufficient corroboration on its own, regardless
       of its `source` or how many other candidates exist.
    2. Independent corroboration — a candidate whose `source` genuinely
       differs both from `provisional_fact`'s own `source` and from every
       other candidate already counted. Shared-origin republication (an
       identical `source` value) never counts, no matter how many
       candidates repeat it — this is the single most important rule
       here, per Section 4a's explicit example: two outlets both
       republishing the same wire report or press release does not count.
       A candidate's `source` matching another *already-counted*
       candidate's `source` is excluded too, so two republications of the
       same story cannot corroborate each other into counting as two
       independent confirmations.

    On success: returns a NEW UAP (does not mutate `provisional_fact` or
    any UAP in `candidate_sources`) with `validation_status` upgraded to
    `VERIFIED` and `evidence` extended with the corroborating source(s) —
    per Section 4a, no new field is introduced; `evidence` is reused.

    On no corroboration found: returns a NEW UAP equivalent to the input,
    `validation_status` unchanged at `PROVISIONAL`. This is a valid,
    expected outcome, not an error.

    Raises ValueError if `provisional_fact` is not itself
    `information_class=FACT`, `validation_status=PROVISIONAL` —
    corroboration is only meaningful for a provisional fact.
    """
    if (
        provisional_fact.information_class != InformationClass.FACT
        or provisional_fact.validation_status != ValidationStatus.PROVISIONAL
    ):
        raise ValueError(
            "corroborate_fact: provisional_fact must have "
            "information_class=FACT and validation_status=PROVISIONAL "
            "(ANALYTICAL_CONTRACT_SPEC.md Section 4a — corroboration is "
            f"only meaningful for a provisional fact); got "
            f"information_class={provisional_fact.information_class!r}, "
            f"validation_status={provisional_fact.validation_status!r}."
        )

    corroborating_evidence: list[str] = []

    # Structured cross-check, checked first: an already-VERIFIED FACT is
    # sufficient corroboration on its own, regardless of its `source`.
    for candidate in candidate_sources:
        if (
            candidate.information_class == InformationClass.FACT
            and candidate.validation_status == ValidationStatus.VERIFIED
        ):
            entry = (
                f"structured cross-check: {candidate.source} "
                f"(packet id: {candidate.id})"
            )
            if entry not in corroborating_evidence:
                corroborating_evidence.append(entry)

    # Independent corroboration: a candidate's `source` must differ from
    # provisional_fact's own source AND from every other candidate's
    # source already counted (seen_sources starts pre-seeded with
    # provisional_fact's own source for exactly this reason).
    seen_sources: set[str] = {provisional_fact.source}
    for candidate in candidate_sources:
        if candidate.source not in seen_sources:
            seen_sources.add(candidate.source)
            entry = (
                f"independent source: {candidate.source} "
                f"(packet id: {candidate.id})"
            )
            corroborating_evidence.append(entry)

    if not corroborating_evidence:
        return provisional_fact.model_copy(deep=True)

    return provisional_fact.model_copy(
        deep=True,
        update={
            "validation_status": ValidationStatus.VERIFIED,
            "evidence": [*provisional_fact.evidence, *corroborating_evidence],
        },
    )
