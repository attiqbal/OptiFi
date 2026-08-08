"""
extract_structured_claim — Stage 3 unstructured-extraction support
(ENGINE_PIPELINE_SPECIFICATION.md Section 9, Stage 3;
AI_ENGINE_SPEC.md Section 3.1; Never-list item 8).

ai-engine assists data-engine in extracting structured claims from
unstructured text but never self-certifies the result as VERIFIED —
corroboration is data-engine's call (ANALYTICAL_CONTRACT_SPEC.md Section
4a). This function has no `validation_status` parameter of any kind: the
value is hard-coded to PROVISIONAL in the return statement, so there is no
argument a caller can pass to get anything else out of it.
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .generator import ExplanationGenerator


def extract_structured_claim(raw_text: str, generator: ExplanationGenerator) -> UAP:
    prompt = f"Extract a single structured factual claim from this text: {raw_text}"
    extracted = generator.generate(prompt, {"raw_text": raw_text})

    return UAP(
        subject="claim extracted from unstructured text",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result=extracted,
        source="unstructured text (Stage 3 extraction support)",
        producer="ai-engine / Stage 3 unstructured extraction support, AI_ENGINE_SPEC.md Section 3.1",
        confidence=ConfidenceLevel.LOW,
        assumptions=["extraction has not yet been corroborated by data-engine"],
    )
