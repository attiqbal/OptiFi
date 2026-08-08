"""
optifi_optimisation — optimisation-engine.

Implements OPTIMISATION_ENGINE_SPEC.md Section 5.1 (minimise variance for
a target return) only. Section 5.2 (maximise Sharpe ratio), Section 5.3
(the efficient frontier), the full Mandate constraint taxonomy (Section
6, beyond generic per-asset weight bounds), and Section 8's gate-checking
are all separate, not-yet-implemented future work.
"""

from .mean_variance import minimize_variance

__all__ = ["minimize_variance"]
