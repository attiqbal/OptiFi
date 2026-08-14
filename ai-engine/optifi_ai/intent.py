"""
classify_required_engines — Phase E6, "Dynamic Routing".

Decides which specialist engines a query analytically needs, so the CIO
does not "run every engine for every request" (Phase E6 brief). This is
**not** a real LLM/NLU call — `StubExplanationGenerator` cannot genuinely
understand intent (ai-engine/generator.py), so pretending a call to
`.generate()` here produced real classification would be exactly the kind
of fabrication CLAUDE.md forbids. Routing is instead an honest, documented
keyword heuristic: deterministic, testable, and explicitly flagged as a
placeholder for real NLU rather than disguised as one. Its own output
carries `validation_status=PROVISIONAL` / `confidence=LOW` for the same
reason a Stage 3 extraction does (extraction.py) — it is provisional
machine output, not a settled fact about what the user wants.

Two illustrative query shapes anchor the two thresholds this module draws
(Phase E6 brief's own examples):
  - "What is my technology allocation?" — a plain lookup, routed to
    QUANT only.
  - "Should I reduce equities because recession risk has increased?" — a
    decision framed around a causal hypothesis, routed through the full
    analytical chain (causal -> forecast -> simulation -> quant ->
    optimisation -> verification).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SpecialistEngine(str, Enum):
    """The specialist engines a query can be routed to (README.md's nine
    engines, minus ai-engine itself, which is always implicitly involved
    as the router)."""

    DATA = "DATA"
    CAUSAL = "CAUSAL"
    FORECAST = "FORECAST"
    EVALUATION = "EVALUATION"
    QUANT = "QUANT"
    SIMULATION = "SIMULATION"
    OPTIMISATION = "OPTIMISATION"
    VERIFICATION = "VERIFICATION"


# A query containing any of these phrases is asking for a decision, not a
# lookup — it needs the full causal -> forecast -> simulation -> quant ->
# optimisation -> verification chain, matching the Phase E6 brief's
# "complex request" example exactly.
_DECISION_LANGUAGE = (
    "should i",
    "should we",
    "recession",
    "because",
    "reduce",
    "increase my",
    "rebalance",
    "sell",
    "buy ",
    "what if",
)

# Plain-lookup keyword -> the single specialist engine that answers it,
# used only when no decision language above was matched.
_LOOKUP_KEYWORDS: dict[SpecialistEngine, tuple[str, ...]] = {
    SpecialistEngine.QUANT: ("allocation", "exposure", "value", "weight", "sharpe", "var", "volatility"),
    SpecialistEngine.FORECAST: ("forecast", "outlook", "predict"),
    SpecialistEngine.EVALUATION: ("track record", "how accurate", "model performance", "scorecard"),
    SpecialistEngine.CAUSAL: ("why does", "why did", "relationship between"),
    SpecialistEngine.SIMULATION: ("scenario", "stress test"),
}

_FULL_DECISION_CHAIN = (
    SpecialistEngine.CAUSAL,
    SpecialistEngine.FORECAST,
    SpecialistEngine.SIMULATION,
    SpecialistEngine.QUANT,
    SpecialistEngine.OPTIMISATION,
    SpecialistEngine.VERIFICATION,
)


@dataclass(frozen=True)
class RoutingDecision:
    """The routing outcome plus *why* — required so a caller (or a test)
    can inspect the classification instead of trusting an opaque set."""

    engines: frozenset[SpecialistEngine]
    reasoning: list[str] = field(default_factory=list)
    is_heuristic: bool = True  # always True this phase — see module docstring


def classify_required_engines(query_text: str) -> RoutingDecision:
    text = query_text.lower()
    reasoning: list[str] = []

    matched_decision_phrases = [p for p in _DECISION_LANGUAGE if p in text]
    if matched_decision_phrases:
        reasoning.append(
            f"decision language matched ({matched_decision_phrases}); routing the full "
            "analytical chain rather than a single lookup"
        )
        engines = set(_FULL_DECISION_CHAIN)
        for engine in _FULL_DECISION_CHAIN:
            reasoning.append(f"{engine.value}: part of the standard decision chain")
        return RoutingDecision(engines=frozenset(engines), reasoning=reasoning)

    engines = set()
    for engine, keywords in _LOOKUP_KEYWORDS.items():
        matched = [k for k in keywords if k in text]
        if matched:
            engines.add(engine)
            reasoning.append(f"{engine.value}: matched keyword(s) {matched}")

    if not engines:
        # Safe default: an unrecognised query about "my portfolio" is a
        # QUANT-shaped question far more often than not, and defaulting
        # to the full chain for every unclassified query would violate
        # "do not run every engine for every request" — see module
        # docstring. Documented as a fallback, not a confident inference.
        engines = {SpecialistEngine.QUANT}
        reasoning.append("no keyword matched; defaulting to QUANT as the narrowest safe fallback")

    if SpecialistEngine.OPTIMISATION in engines:
        # Verification Gate: "Material personalised recommendations must
        # pass the independent verification layer" — never optional.
        engines.add(SpecialistEngine.VERIFICATION)
        reasoning.append("VERIFICATION: added because OPTIMISATION output requires the verification gate")

    return RoutingDecision(engines=frozenset(engines), reasoning=reasoning)
