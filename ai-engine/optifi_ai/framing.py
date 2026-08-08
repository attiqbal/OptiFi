"""
frame_candidate — Stage 10, Candidate Framing & Explanation
(ENGINE_PIPELINE_SPECIFICATION.md Section 9, Stage 10;
AI_ENGINE_SPEC.md Section 3.2; Never-list item 2).

Hard constraint: ai-engine must not invent, alter, or substitute a
different financial action, or change a candidate's quantitative figures.
This module enforces that structurally rather than post-hoc: the generator
is never given `candidate.result` in its prompt or context, so there is no
code path through which generated text could end up inside
`original_figures` — that field is always a direct, untouched copy of
`candidate.result`.
"""

from optifi_shared import InformationClass, UAP, ValidationStatus

from .generator import ExplanationGenerator


def frame_candidate(
    candidate: UAP,
    generator: ExplanationGenerator,
    upstream_context: list[UAP] | None = None,
) -> UAP:
    upstream_context = upstream_context or []

    # Deliberately excludes candidate.result: the generator narrates the
    # candidate, it is never shown the figures it would need to alter them.
    prompt = f"Explain and contextualise the candidate: {candidate.subject}"
    context = {
        "candidate_subject": candidate.subject,
        "candidate_information_class": candidate.information_class.value,
        "upstream_subjects": [u.subject for u in upstream_context],
    }
    narrative = generator.generate(prompt, context)

    return UAP(
        subject=candidate.subject,
        information_class=InformationClass.JUDGEMENT,
        validation_status=ValidationStatus.PROVISIONAL,
        result={"narrative": narrative, "original_figures": candidate.result},
        source="ai-engine candidate framing",
        producer="ai-engine / candidate framing, AI_ENGINE_SPEC.md Section 3.2",
        confidence=candidate.confidence,
        dependencies=[candidate.id, *(u.id for u in upstream_context)],
    )
