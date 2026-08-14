"""
Explanation Structure — Phase E6 brief: user-facing answers must clearly
separate what happened (FACT), what models suggest (ESTIMATE), what OptiFi
concludes (JUDGEMENT), what could change the conclusion, confidence/
uncertainty, a suggested action or NO ACTION, and why.

`CIOExplanation` assembles that structure deterministically from real UAPs
— no generator call is needed to decide which bucket a UAP belongs in
(`information_class` already says so). `present_for_sophistication` is the
only place a generator produces prose, and only varies *narrative depth*:
per PRODUCT_VISION.md Section 10, sophistication tiers must never change
the underlying analytical truth, only how much of it is spelled out.

Directive-language guard: `AI_ENGINE_SPEC.md` Section 4, item 5 ("never use
directive investment language — no 'Buy X,' no 'Sell X'") is one of the
Never-list items `ai-engine/__init__.py` already documents as *not*
mechanically checkable without a real LLM judging semantic content. This
module adds one narrow, best-effort mechanical check anyway — scanning
literal generator output for "buy "/"sell " immediately followed by a
capitalised token — and redacts a match with a logged note. This is a
heuristic safety net, not a semantic guarantee: it catches the literal
phrasing the spec names as its own example, nothing more.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from optifi_shared import InformationClass, UAP, ValidationStatus

from .generator import ExplanationGenerator
from .roadblock import Roadblock
from .verification_gate import CIOVerdictHandling, GateResult


class UserSophistication(str, Enum):
    BEGINNER = "BEGINNER"
    INFORMED = "INFORMED"
    PROFESSIONAL = "PROFESSIONAL"


_DIRECTIVE_LANGUAGE = re.compile(r"\b(buy|sell)\s+[A-Z][A-Za-z0-9.\-]*", re.IGNORECASE)


@dataclass(frozen=True)
class CIOExplanation:
    facts: list[UAP]
    estimates: list[UAP]
    judgements: list[UAP]
    disagreement_notes: list[str]
    non_verified_disclosures: list[str]
    roadblocks: list[Roadblock]
    suggested_action: str
    why_ids: list[str] = field(default_factory=list)


def _suggested_action(candidate: UAP | None, gate_result: GateResult | None) -> str:
    if candidate is None or gate_result is None:
        return "NO ACTION"
    if gate_result.excluded:
        # REJECT — VERIFICATION_FRAMEWORK.md Section 8: omitted entirely,
        # never presented as a basis for action.
        return "NO ACTION — candidate failed independent verification (REJECT)"
    if gate_result.handling in (CIOVerdictHandling.REVISE, CIOVerdictHandling.INSUFFICIENT_EVIDENCE):
        return f"NO ACTION — conclusion deferred pending {gate_result.handling.value.lower()}"
    # PASS or PASS_WITH_CAUTION: the candidate stands, but this module
    # never invents or rewords the action itself (AI_ENGINE_SPEC.md
    # Section 4, item 2) — it points at the candidate's own subject,
    # which is upstream, verified-through-Stage-9b text, not generated
    # text this module could distort.
    caution = " (verification: PASS WITH CAUTION — see disclosures)" if gate_result.handling == CIOVerdictHandling.PASS_WITH_CAUTION else ""
    return f"Candidate available for consideration: {candidate.subject}{caution}"


def build_explanation(
    uaps: list[UAP],
    disagreement_notes: list[str] | None = None,
    roadblocks: list[Roadblock] | None = None,
    candidate: UAP | None = None,
    gate_result: GateResult | None = None,
) -> CIOExplanation:
    facts = [u for u in uaps if u.information_class == InformationClass.FACT]
    estimates = [u for u in uaps if u.information_class == InformationClass.ESTIMATE]
    judgements = [u for u in uaps if u.information_class == InformationClass.JUDGEMENT]

    non_verified = [
        f"'{u.subject}' has validation_status={u.validation_status.value}, not VERIFIED."
        for u in uaps
        if u.validation_status != ValidationStatus.VERIFIED
    ]

    return CIOExplanation(
        facts=facts,
        estimates=estimates,
        judgements=judgements,
        disagreement_notes=list(disagreement_notes or []),
        non_verified_disclosures=non_verified,
        roadblocks=list(roadblocks or []),
        suggested_action=_suggested_action(candidate, gate_result),
        why_ids=[u.id for u in uaps],
    )


def _redact_directive_language(text: str) -> tuple[str, bool]:
    if not _DIRECTIVE_LANGUAGE.search(text):
        return text, False
    return _DIRECTIVE_LANGUAGE.sub("[directive language redacted]", text), True


def present_for_sophistication(
    explanation: CIOExplanation, level: UserSophistication, generator: ExplanationGenerator
) -> str:
    prompt = "Narrate the following analytical findings for the user."
    context = {
        "fact_subjects": [u.subject for u in explanation.facts],
        "estimate_subjects": [u.subject for u in explanation.estimates],
        "judgement_subjects": [u.subject for u in explanation.judgements],
        "sophistication": level.value,
    }
    narrative, was_redacted = _redact_directive_language(generator.generate(prompt, context))

    lines = [narrative, ""]
    lines.append(f"FACT: {[u.subject for u in explanation.facts] or 'none'}")
    lines.append(f"ESTIMATE: {[u.subject for u in explanation.estimates] or 'none'}")
    lines.append(f"JUDGEMENT: {[u.subject for u in explanation.judgements] or 'none'}")

    if explanation.disagreement_notes:
        lines.append("What could change the conclusion (disagreement): " + "; ".join(explanation.disagreement_notes))
    if explanation.roadblocks:
        lines.append(
            "Roadblocks (missing/stale information): "
            + "; ".join(r.description for r in explanation.roadblocks)
        )
    if explanation.non_verified_disclosures:
        lines.append("Disclosures: " + " ".join(explanation.non_verified_disclosures))
    if was_redacted:
        lines.append("Note: directive investment language was detected and redacted from generated text.")

    lines.append(f"Suggested action: {explanation.suggested_action}")

    # PROFESSIONAL gets the full "Why?" id trace; BEGINNER gets none inline
    # (still traceable via trace_evidence(), just not spelled out in the
    # narrative body); INFORMED gets a count, not the raw ids. Depth only
    # — the underlying explanation object is identical at every level.
    if level == UserSophistication.PROFESSIONAL:
        lines.append(f"Why (evidence ids): {explanation.why_ids}")
    elif level == UserSophistication.INFORMED:
        lines.append(f"Why: traceable to {len(explanation.why_ids)} underlying analytical packet(s).")

    return "\n".join(lines)
