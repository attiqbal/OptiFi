"""
optifi_verification — verification-engine.

Implements VERIFICATION_FRAMEWORK.md's Stage 11 independence-first checks:
the verdict taxonomy (Section 4/5.7), applying a verdict to a UAP's
validation_status (Section 4), provenance-chain resolvability (Section 7),
independent re-derivation of optimisation-engine candidates including a
loss-cap check reusing quant-engine's VaR functions (Section 5.5), an
independent corroboration audit (Section 3/5.1), an independent check
that ai-engine's Stage 10 candidate framing hasn't altered the underlying
figures (Section 6), and independent re-derivation of optimisation-engine's
defined-risk options structure candidates, including a from-scratch
re-check of the naked-call constraint (HEDGING_SPEC.md Section 6/7).
"""

from .apply_verdict import apply_verdict
from .candidate_framing_checks import verify_candidate_framing_unaltered
from .corroboration_audit import audit_corroboration
from .hedging_checks import verify_collar, verify_protective_put
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
    "verify_candidate_framing_unaltered",
    "verify_protective_put",
    "verify_collar",
]
