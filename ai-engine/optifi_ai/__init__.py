"""
optifi_ai — ai-engine.

Implements the checkable subset of AI_ENGINE_SPEC.md's Section 4
"Consolidated Never List": item 2 (never alter a candidate's figures,
Stage 10), item 3 (never mathematically resolve multi-model disagreement,
Stage 12), item 8 (never self-certify Stage 3 extraction as VERIFIED), and
item 9 (never omit a non-VERIFIED disclosure, Stage 13).

Deliberately does not implement items 1, 4, 5, 6, 7 of that list — those
concern constraints on natural-language content (no directive investment
language, no execution surface, no personalised Tier 3 figures, no
inventing specialist-owned figures like the Capital Efficiency Score) and
on avoiding deterministic calculations already owned elsewhere. None of
them are mechanically checkable against a stub generator's output the way
items 2/3/8/9 are; they depend on judging the semantic content of
real generated text, which requires an actual LLM integration this phase
does not build.

No function in this package calls a real LLM provider, holds an API key,
or makes a network request — every function takes an `ExplanationGenerator`
and the only implementation provided is `StubExplanationGenerator`.
"""

from .disagreement import (
    DISAGREEMENT_TOLERANCE,
    group_by_disagreement_set,
    has_genuine_disagreement,
    synthesize_with_disagreement_preserved,
)
from .disclosure import explain_with_disclosure
from .extraction import extract_structured_claim
from .framing import frame_candidate
from .generator import ExplanationGenerator, StubExplanationGenerator

__all__ = [
    "ExplanationGenerator",
    "StubExplanationGenerator",
    "frame_candidate",
    "extract_structured_claim",
    "group_by_disagreement_set",
    "has_genuine_disagreement",
    "synthesize_with_disagreement_preserved",
    "DISAGREEMENT_TOLERANCE",
    "explain_with_disclosure",
]
