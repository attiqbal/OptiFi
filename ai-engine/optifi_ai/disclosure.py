"""
explain_with_disclosure — Stage 13, User-Facing Explanation
(ENGINE_PIPELINE_SPECIFICATION.md Section 9, Stage 13;
AI_ENGINE_SPEC.md Section 3.4; Never-list item 9).

A non-VERIFIED item reaching the user must say so. This function does not
rely on the generator to mention validation status — the disclosure is
appended by code, unconditionally, for every input UAP whose
`validation_status` is not VERIFIED, regardless of what the generator's
text does or does not say.
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .generator import ExplanationGenerator


def explain_with_disclosure(uaps: list[UAP], generator: ExplanationGenerator) -> UAP:
    prompt = "Explain the following analytical outputs to the user."
    context = {"subjects": [u.subject for u in uaps]}
    narrative = generator.generate(prompt, context)

    # Appended by code, not the generator: independent of whatever the
    # generated narrative does or doesn't say about validation status.
    disclosures = [
        f"Note: '{u.subject}' has validation_status={u.validation_status.value}, not VERIFIED."
        for u in uaps
        if u.validation_status != ValidationStatus.VERIFIED
    ]

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
