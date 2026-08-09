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

REJECTED-input guard (VERIFICATION_FRAMEWORK.md Section 8): a REJECTED
output must not be used downstream without an explicit, logged override.
Before this fix, nothing enforced that — frame_candidate accepted a
REJECTED candidate exactly like any other and, worse, unconditionally
overwrote its own output's validation_status to PROVISIONAL regardless of
the input's actual status, silently erasing the rejection. Now, a
REJECTED candidate raises by default; proceeding requires an explicit
override_reason, which is then recorded in the output's own limitations
— the "logged" half of "explicit, logged override." Deliberately scoped
to REJECTED only: CONFLICTED/STALE/INCOMPLETE are not blocked here (a
separate, future consideration, not this fix).

Confidence capping: this function's own output always carries
validation_status=PROVISIONAL, regardless of the input candidate's
status — framing is interpretive and Stage 11's independent check hasn't
run on it yet, so it can never itself be more settled than PROVISIONAL.
UAP's own model-level guardrail (shared/optifi_shared/uap.py) requires
HIGH confidence to pair with a settled status (VERIFIED/SUPERSEDED).
Forwarding a HIGH-confidence input candidate's confidence unchanged
would therefore always fail to construct — capped at MODERATE instead,
since forwarding is otherwise the correct default (a candidate's own
stated confidence is meaningful context for the framing) and MODERATE is
the highest confidence a PROVISIONAL packet is allowed to claim.
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .generator import ExplanationGenerator


def frame_candidate(
    candidate: UAP,
    generator: ExplanationGenerator,
    upstream_context: list[UAP] | None = None,
    override_rejection: bool = False,
    override_reason: str | None = None,
) -> UAP:
    override_note: str | None = None
    if candidate.validation_status == ValidationStatus.REJECTED:
        if not override_rejection:
            raise ValueError(
                "frame_candidate: candidate.validation_status is REJECTED. "
                "A REJECTED output must not be used downstream without an "
                "explicit, logged override (VERIFICATION_FRAMEWORK.md "
                "Section 8). Pass override_rejection=True with a real "
                "override_reason to proceed anyway."
            )
        if not override_reason or not override_reason.strip():
            raise ValueError(
                "frame_candidate: override_rejection=True requires a "
                "non-empty override_reason — the override must be "
                "explicit and logged, not silent."
            )
        override_note = f"PROCEEDED DESPITE REJECTED INPUT — override_reason: {override_reason.strip()}"

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

    # This output is always PROVISIONAL (see module docstring), so HIGH
    # confidence is never a valid pairing regardless of what the input
    # candidate itself claimed — capped, not forwarded blindly.
    output_confidence = (
        ConfidenceLevel.MODERATE if candidate.confidence == ConfidenceLevel.HIGH else candidate.confidence
    )

    return UAP(
        subject=candidate.subject,
        information_class=InformationClass.JUDGEMENT,
        validation_status=ValidationStatus.PROVISIONAL,
        result={"narrative": narrative, "original_figures": candidate.result},
        source="ai-engine candidate framing",
        producer="ai-engine / candidate framing, AI_ENGINE_SPEC.md Section 3.2",
        confidence=output_confidence,
        dependencies=[candidate.id, *(u.id for u in upstream_context)],
        limitations=[override_note] if override_note else [],
    )
