"""
optifi_causal — causal-engine.

Implements CausalClaim (CAUSAL_ENGINE_SPEC.md Section 5) — the structural
contract every causal claim must satisfy, and the correlation-causation
guardrail — without implementing, choosing, or stubbing any causal
inference methodology (Section 3 remains undecided).
"""

from .causal_claim import CausalClaim

__all__ = ["CausalClaim"]
