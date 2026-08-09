"""
explain_with_disclosure — Stage 13, User-Facing Explanation
(ENGINE_PIPELINE_SPECIFICATION.md Section 9, Stage 13;
AI_ENGINE_SPEC.md Section 3.4; Never-list item 9).

A non-VERIFIED item reaching the user must say so. This function does not
rely on the generator to mention validation status — the disclosure is
appended by code, unconditionally, for every input UAP whose
`validation_status` is not VERIFIED, regardless of what the generator's
text does or does not say.

Disclosure completeness is never silently assumed. Every UAP in `uaps`
that has non-empty `dependencies`/`provenance_chain` has those references
recursively resolved and checked too — the same traversal already proven
correct in the vertical slice's evidence-chain test — using `known_uaps`
(an id -> UAP lookup) as the resolution source, alongside `uaps` itself
(so a caller who passes several related UAPs together doesn't need
`known_uaps` just to cross-reference them). Any reference that cannot be
resolved this way does NOT get silently dropped: it produces its own
explicit "could not be checked" note naming which UAP has the unresolved
reference and which reference id it is, precisely because an unresolved
ancestor's trust level is genuinely unknown, not because it's assumed
safe. This is deliberately not a hard error — blocking a user-facing
explanation entirely because full ancestry can't be resolved would be the
wrong tradeoff — but it also means this function can never again produce
a clean, empty-looking disclosure for a UAP whose upstream chain wasn't
actually checked.

A UAP with no dependencies/provenance_chain at all is a true leaf — there
is nothing to resolve, so it never generates an incompleteness note.
"""

from __future__ import annotations

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .generator import ExplanationGenerator


def explain_with_disclosure(
    uaps: list[UAP],
    generator: ExplanationGenerator,
    known_uaps: dict[str, UAP] | None = None,
) -> UAP:
    prompt = "Explain the following analytical outputs to the user."
    context = {"subjects": [u.subject for u in uaps]}
    narrative = generator.generate(prompt, context)

    reachable, unresolved_by_referencer = _walk_all_dependencies(uaps, known_uaps or {})
    reachable_by_id = {u.id: u for u in reachable}

    # Appended by code, not the generator: independent of whatever the
    # generated narrative does or doesn't say about validation status.
    disclosures = [
        f"Note: '{u.subject}' has validation_status={u.validation_status.value}, not VERIFIED."
        for u in reachable
        if u.validation_status != ValidationStatus.VERIFIED
    ]
    for referencer_id, missing_ids in unresolved_by_referencer.items():
        referencer = reachable_by_id[referencer_id]
        disclosures.append(
            f"Note: '{referencer.subject}' has upstream reference(s) that "
            "could not be resolved, so their validation_status is unknown "
            "and full disclosure cannot be guaranteed: "
            f"{sorted(missing_ids)}."
        )

    full_text = narrative
    if disclosures:
        full_text = narrative + "\n\n" + "\n".join(disclosures)

    return UAP(
        subject="user-facing explanation",
        information_class=InformationClass.JUDGEMENT,
        validation_status=ValidationStatus.PROVISIONAL,
        result=full_text,
        source="ai-engine user-facing explanation",
        producer="ai-engine / user-facing explanation, AI_ENGINE_SPEC.md Section 3.4",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=[u.id for u in uaps],
        limitations=disclosures,
    )


def _walk_all_dependencies(
    start_uaps: list[UAP], known_uaps: dict[str, UAP]
) -> tuple[list[UAP], dict[str, set[str]]]:
    """
    Recursively resolves every UAP reachable from `start_uaps` via
    `dependencies`/`provenance_chain`. A reference is resolvable either
    because it points at one of `start_uaps` itself (so a caller passing
    several related UAPs together doesn't need `known_uaps` just to
    cross-reference them), or because it's found in `known_uaps`.

    Returns (every reachable UAP including `start_uaps`, deduplicated by
    id; a mapping of referencing UAP id -> the set of its own
    dependency/provenance ids that could not be resolved either way).
    """
    reached: dict[str, UAP] = {u.id: u for u in start_uaps}
    unresolved_by_referencer: dict[str, set[str]] = {}
    to_expand: list[UAP] = list(start_uaps)
    expanded: set[str] = set()

    while to_expand:
        current = to_expand.pop()
        if current.id in expanded:
            continue
        expanded.add(current.id)

        for ref_id in [*current.dependencies, *current.provenance_chain]:
            if ref_id in reached:
                continue
            packet = known_uaps.get(ref_id)
            if packet is None:
                unresolved_by_referencer.setdefault(current.id, set()).add(ref_id)
                continue
            reached[ref_id] = packet
            to_expand.append(packet)

    return list(reached.values()), unresolved_by_referencer
