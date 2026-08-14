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
and the only implementation provided is `StubExplanationGenerator`. This
also holds for Phase E6's CIO orchestration layer (`orchestrator.py` and
friends) — see `docs/CIO_ORCHESTRATION_SPEC.md` and
`instruction_hierarchy.py` for the full accounting of what is/isn't
mechanically enforced.

Import boundary (Phase E6): `verification_gate.py`, `explanation.py`, and
`orchestrator.py` depend on `optifi_verification` — and `orchestrator.py`
additionally depends on `optifi_causal`/`optifi_forecast`/
`optifi_simulation`/`optifi_optimisation` — to call real specialist
functions for its worked routing examples. Before Phase E6, this
package's only external dependency was `optifi_shared`, and
`verification-engine`'s own tests already depend on this package (for
`frame_candidate`/`StubExplanationGenerator`, used to verify Stage 10
output). Eagerly re-exporting the heavy CIO modules here would make every
existing consumer of `optifi_ai` (verification-engine included) newly
require five more packages just to import this one — turning a one-way
pipeline dependency into a practical installation cycle. To avoid that,
this `__init__.py` deliberately keeps re-exporting only the
`optifi_shared`-only-dependent modules; `verification_gate`,
`explanation`, and `orchestrator` are still real, tested, and fully
functional, just imported directly
(`from optifi_ai.orchestrator import CIOOrchestrator`) by whoever
actually wants the CIO layer, rather than pulled in by importing
`optifi_ai` at all.
"""

from .disagreement import (
    DISAGREEMENT_TOLERANCE,
    group_by_disagreement_set,
    has_genuine_disagreement,
    synthesize_with_disagreement_preserved,
)
from .disclosure import explain_with_disclosure
from .evidence_trace import trace_evidence
from .extraction import extract_structured_claim
from .framing import frame_candidate
from .generator import ExplanationGenerator, StubExplanationGenerator
from .intent import classify_required_engines, RoutingDecision, SpecialistEngine
from .roadblock import check_staleness, detect_missing_dependencies, Roadblock

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
    "trace_evidence",
    "SpecialistEngine",
    "RoutingDecision",
    "classify_required_engines",
    "Roadblock",
    "detect_missing_dependencies",
    "check_staleness",
]
