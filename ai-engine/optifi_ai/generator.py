"""
ExplanationGenerator — the swappable text-generation seam for ai-engine.

No function in this package calls an LLM provider, holds an API key, or
makes a network request. Every function that needs generated text takes a
generator object satisfying this Protocol and calls it; which concrete
generator is passed in is a decision left entirely to the caller. Wiring in
a real LLM provider later means writing one class that implements
`generate(prompt, context) -> str` — nothing in `framing.py`,
`extraction.py`, `disagreement.py`, or `disclosure.py` would need to change.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ExplanationGenerator(Protocol):
    def generate(self, prompt: str, context: dict[str, Any]) -> str: ...


class StubExplanationGenerator:
    """
    A placeholder generator with no real LLM connected — no network call,
    no API key, no vendor. Every string it returns is prefixed so it can
    never be mistaken for real model output further down the pipeline.
    """

    def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return (
            f"[STUB — no real LLM connected] "
            f"prompt={prompt!r} context_keys={sorted(context.keys())!r}"
        )
