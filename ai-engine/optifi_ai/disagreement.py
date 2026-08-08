"""
Disagreement grouping and preservation — Stage 12, CIO / Manager Synthesis
(ENGINE_PIPELINE_SPECIFICATION.md Section 7 and Section 9 Stage 12;
AI_ENGINE_SPEC.md Section 3.3; Never-list item 3).

ai-engine must not mathematically resolve disagreement between multiple
ESTIMATE entries sharing a subject — it explains disagreement, it does not
pick or average a winner. This module groups UAPs that share a
`disagreement_set_ref`, decides whether a group's disagreement is genuine
(as opposed to floating-point noise), and synthesises across groups while
guaranteeing every member of a genuinely-disagreeing group is preserved in
the output's `dependencies` — none silently dropped.
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .generator import ExplanationGenerator

# Numeric results within this tolerance of each other are treated as
# floating-point noise from independent computations, not genuine
# disagreement. Chosen well above typical float64 rounding error (~1e-15)
# but far below any economically meaningful difference between models.
DISAGREEMENT_TOLERANCE = 1e-6


def group_by_disagreement_set(uaps: list[UAP]) -> dict[str, list[UAP]]:
    groups: dict[str, list[UAP]] = {}
    for uap in uaps:
        if uap.disagreement_set_ref is not None:
            groups.setdefault(uap.disagreement_set_ref, []).append(uap)
    return groups


def has_genuine_disagreement(group: list[UAP]) -> bool:
    if len(group) < 2:
        return False

    values = [u.result for u in group]

    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return (max(values) - min(values)) > DISAGREEMENT_TOLERANCE

    # Non-numeric results (e.g. dicts, strings) have no meaningful
    # tolerance to apply — fall back to exact-value comparison via a
    # string representation, since `result` (typed Any) is not guaranteed
    # hashable on its own.
    return len({str(v) for v in values}) > 1


def synthesize_with_disagreement_preserved(
    groups: dict[str, list[UAP]], generator: ExplanationGenerator
) -> UAP:
    prompt = "Synthesize across the following specialist outputs, explaining any disagreement rather than resolving it."
    context = {
        "disagreement_set_refs": list(groups.keys()),
        "group_sizes": {ref: len(group) for ref, group in groups.items()},
    }
    narrative = generator.generate(prompt, context)

    dependencies: list[str] = []
    disagreement_notes: list[str] = []
    for ref, group in groups.items():
        # Every member of every group is preserved as a dependency —
        # genuinely-disagreeing groups are never truncated to a single
        # "winning" member.
        dependencies.extend(u.id for u in group)
        if has_genuine_disagreement(group):
            disagreement_notes.append(
                f"genuine disagreement in group '{ref}' across {len(group)} members "
                f"(values: {[u.result for u in group]}) — not resolved, only reported"
            )

    return UAP(
        subject="CIO synthesis across disagreement groups",
        information_class=InformationClass.JUDGEMENT,
        validation_status=ValidationStatus.PROVISIONAL,
        result=narrative,
        source="ai-engine CIO synthesis",
        producer="ai-engine / CIO synthesis, AI_ENGINE_SPEC.md Section 3.3",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=dependencies,
        limitations=disagreement_notes,
    )
