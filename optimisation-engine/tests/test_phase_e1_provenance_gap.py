"""
Phase E1 hardening — required test category #7: "missing provenance on a
production analytical pathway."

This test does NOT prove a fix — it honestly documents a genuine,
currently-open gap, deliberately left open rather than silently resolved.
See the Phase E1 deliverable's "Section 3 — Provenance Mandatory" write-up
for the full options/trade-offs analysis: making provenance genuinely
MANDATORY on optimisation-engine's production entry points would require
either (a) making covariance_source_id/expected_returns_source_id
required parameters — a breaking signature change to two already-shipped,
widely-tested functions, and to every other engine with the same
raw-dict-input shape — or (b) a parallel, UAP-typed "production" API
surface alongside the existing raw-dict one. Both are real, competing
architectural decisions with genuine trade-offs; this task does not
silently pick one. This test exists so the gap is verified and visible,
not just asserted in prose.

Existing coverage: test_source_id_dependencies.py's
test_minimize_variance_dependencies_and_provenance_empty_when_source_ids_omitted
already demonstrates the same underlying fact for minimize_variance. This
file adds the sharper, more adversarial framing test category #7 asks
for specifically: a solved, real, otherwise-unremarkable portfolio
candidate produced from wholly anonymous inputs, indistinguishable from
hand-typed numbers, with zero traceability anywhere in the result.
"""

from optifi_optimisation import minimize_variance_with_loss_cap

# Deliberately NOT sourced from any UAP, any engine, any id — exactly
# what a caller could type by hand. Nothing in optimisation-engine's
# current production entry points prevents this from being treated
# identically to genuine, provenance-backed quant-engine output.
ANONYMOUS_EXPECTED_RETURNS = {"A": 0.05, "B": 0.08, "C": 0.12}
ANONYMOUS_COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0, "C": 0.0},
    "B": {"A": 0.0, "B": 0.09, "C": 0.0},
    "C": {"A": 0.0, "B": 0.0, "C": 0.16},
}


def test_optimiser_currently_accepts_wholly_anonymous_inputs_without_complaint():
    """
    Documents the gap, does not close it: a production entry point
    (minimize_variance_with_loss_cap) currently succeeds on inputs with
    no traceable origin at all -- no covariance_source_id,
    no expected_returns_source_id, no upstream UAP anywhere -- and
    produces a fully-formed, otherwise-legitimate-looking portfolio
    result. Nothing about the resulting UAP itself signals that its
    numeric inputs were anonymous.
    """
    result = minimize_variance_with_loss_cap(
        ANONYMOUS_EXPECTED_RETURNS,
        ANONYMOUS_COVARIANCE,
        target_return=0.09,
        portfolio_value=1_000_000.0,
        max_single_period_loss=1_000_000.0,
        confidence_level=0.95,
    )

    # It succeeds — this is the gap, not a bug in this specific function.
    assert abs(sum(result.result["weights"].values()) - 1.0) < 1e-6

    # And nothing in the result traces back to where the numbers came
    # from — dependencies/provenance_chain are silently empty, not
    # flagged as INCOMPLETE or otherwise marked as provenance-less.
    assert result.dependencies == []
    assert result.provenance_chain == []
    assert result.validation_status.value != "INCOMPLETE"
