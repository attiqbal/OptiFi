"""
Tests for ExplanationGenerator / StubExplanationGenerator
(AI_ENGINE_SPEC.md Section 3, generator seam).
"""

from optifi_ai import ExplanationGenerator, StubExplanationGenerator


def test_stub_satisfies_the_protocol():
    assert isinstance(StubExplanationGenerator(), ExplanationGenerator)


def test_stub_output_is_clearly_labeled_as_a_placeholder():
    generator = StubExplanationGenerator()
    output = generator.generate("some prompt", {"key": "value"})
    assert output.startswith("[STUB — no real LLM connected]")


def test_stub_reflects_prompt_and_context_keys_without_a_network_call():
    generator = StubExplanationGenerator()
    output = generator.generate("explain X", {"a": 1, "b": 2})
    assert "explain X" in output
    assert "'a'" in output and "'b'" in output
