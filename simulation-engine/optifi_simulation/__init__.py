"""
optifi_simulation — simulation-engine.

Implements ScenarioResult (SIMULATION_ENGINE_SPEC.md Sections 7/8) — the
structural contract every scenario simulation output must satisfy, and
the mandatory-range guardrail (since Phase E4, strengthened to require
genuine range width too) — without implementing, choosing, or stubbing
any scenario propagation algorithm philosophy beyond what Phase E4
implements concretely: a curated preset scenario library
(`scenario_library.py`) and real propagation over `causal-engine`'s
transmission graph and `quant-engine`'s empirical/deterministic
sensitivities (`propagation.py`).
"""

from .propagation import propagate_scenario
from .scenario_library import get_scenario, ScenarioDefinition, SCENARIO_LIBRARY
from .scenario_result import ScenarioResult

__all__ = [
    "ScenarioResult",
    "ScenarioDefinition",
    "SCENARIO_LIBRARY",
    "get_scenario",
    "propagate_scenario",
]
