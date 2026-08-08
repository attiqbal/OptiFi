"""
optifi_simulation — simulation-engine.

Implements ScenarioResult (SIMULATION_ENGINE_SPEC.md Sections 7/8) — the
structural contract every scenario simulation output must satisfy, and the
mandatory-range guardrail — without implementing, choosing, or stubbing
any scenario propagation algorithm (Section 6 remains undecided,
inheriting CAUSAL_ENGINE_SPEC.md Section 3's methodology-agnosticism).
"""

from .scenario_result import ScenarioResult

__all__ = ["ScenarioResult"]
