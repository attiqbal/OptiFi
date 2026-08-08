"""
optifi_verification — verification-engine.

Implements VERIFICATION_FRAMEWORK.md's Stage 11 independence-first checks:
the verdict taxonomy (Section 4/5.7), applying a verdict to a UAP's
validation_status (Section 4), provenance-chain resolvability (Section 7),
independent re-derivation of optimisation-engine candidates including a
loss-cap check reusing quant-engine's VaR functions (Section 5.5), and an
independent corroboration audit (Section 3/5.1).
"""

from .apply_verdict import apply_verdict
from .corroboration_audit import audit_corroboration
from .optimisation_checks import verify_loss_cap_candidate, verify_optimisation_candidate
from .provenance import check_provenance_resolvable
from .verdict import FailureCategory, Verdict, VerdictType

__all__ = [
    "Verdict",
    "VerdictType",
    "FailureCategory",
    "apply_verdict",
    "check_provenance_resolvable",
    "verify_optimisation_candidate",
    "verify_loss_cap_candidate",
    "audit_corroboration",
]
