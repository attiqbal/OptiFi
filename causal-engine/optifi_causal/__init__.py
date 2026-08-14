"""
optifi_causal — causal-engine.

Implements CausalClaim (CAUSAL_ENGINE_SPEC.md Section 5) — the structural
contract every causal claim must satisfy, and the correlation-causation
guardrail — without implementing, choosing, or stubbing any causal
inference methodology (Section 3 remains undecided). Since Phase E4, also
implements TransmissionGraph — pure graph plumbing (indexing, multi-hop
pathway discovery) over CausalClaim edges, used by `simulation-engine` to
propagate a scenario along supported economic pathways.
"""

from .causal_claim import CausalClaim
from .transmission_graph import DEFAULT_MAX_DEPTH, Pathway, TransmissionGraph

__all__ = ["CausalClaim", "TransmissionGraph", "Pathway", "DEFAULT_MAX_DEPTH"]
