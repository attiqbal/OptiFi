"""
optifi_optimisation — optimisation-engine.

Implements OPTIMISATION_ENGINE_SPEC.md Section 5.1 (minimise variance for
a target return), that same problem with a mandate single-period loss cap
enforced as a solver constraint (Section 5.1a), Section 5.2 (maximum
Sharpe ratio / tangency portfolio), and Section 5.3 (the efficient
frontier). The full Mandate constraint taxonomy (Section 6, beyond
generic per-asset weight bounds and the loss cap) and Section 8's
gate-checking remain separate, not-yet-implemented future work.
"""

from .frontier import efficient_frontier, maximum_sharpe_ratio
from .mean_variance import minimize_variance, minimize_variance_with_loss_cap

__all__ = [
    "minimize_variance",
    "minimize_variance_with_loss_cap",
    "efficient_frontier",
    "maximum_sharpe_ratio",
]
