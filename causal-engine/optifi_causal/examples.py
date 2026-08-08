"""
Illustrative usage of CausalClaim — not a real causal finding.

`example_rate_cut_mortgage_claim` demonstrates the CausalClaim shape and
guardrail using an illustrative UK-base-rate-to-mortgage-rate claim. It is
not a real causal finding and is not derived from any real inference
process — it does not constitute an implementation of `causal-engine`,
which remains undecided per CAUSAL_ENGINE_SPEC.md Section 3.
"""

from optifi_shared import ConfidenceLevel, ValidationStatus

from .causal_claim import CausalClaim


def example_rate_cut_mortgage_claim() -> CausalClaim:
    """
    Illustrative causal claim: UK base rate cuts influencing mortgage
    refinancing rates (CAUSAL_ENGINE_SPEC.md, Section 5).

    Demonstrates the CausalClaim shape and the correlation-causation
    guardrail. This is not a real causal finding — it is not derived from
    any real inference process, historical data, or model, and no causal
    inference methodology is implemented or chosen here
    (CAUSAL_ENGINE_SPEC.md Section 3 remains undecided).
    """
    return CausalClaim(
        subject="UK base rate cuts -> mortgage refinancing rates",
        validation_status=ValidationStatus.PROVISIONAL,
        result=(
            "A reduction in the UK base rate is associated with lower "
            "mortgage refinancing rates"
        ),
        source="illustrative example — not a real data source",
        producer="causal-engine (illustrative) / CAUSAL_ENGINE_SPEC.md Section 5",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id="entity:uk-base-rate",
        effect_entity_id="entity:uk-mortgage-refinancing-rate",
        mechanism=(
            "Mortgage lenders' funding costs are directly tied to the base "
            "rate; when the base rate falls, wholesale funding costs fall, "
            "and lenders pass at least part of that reduction through to "
            "mortgage pricing to remain competitive."
        ),
        limitations=[
            "illustrative only — not derived from any real inference "
            "process, historical data, or model",
        ],
    )
