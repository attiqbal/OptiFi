"""
Illustrative usage of ScenarioResult — not a real simulation output.

`example_rate_cut_gilt_impact` demonstrates the ScenarioResult shape and
guardrails using an illustrative UK-base-rate-cut-to-Gilts scenario,
thematically consistent with `causal-engine`'s existing rate-cut
CausalClaim example. It is not a real simulation output and is not
derived from any real propagation process — it does not constitute an
implementation of `simulation-engine`'s propagation mechanism, which
remains undecided per SIMULATION_ENGINE_SPEC.md Section 6.
"""

from optifi_shared import ConfidenceLevel, ValidationStatus

from .scenario_result import ScenarioResult


def example_rate_cut_gilt_impact() -> ScenarioResult:
    """
    Illustrative scenario result: UK base rate cut, impact on UK Gilts
    (SIMULATION_ENGINE_SPEC.md, Sections 7/8).

    Illustrative only — not a real simulation output, not derived from
    any real propagation process, historical data, or model. No scenario
    propagation algorithm is implemented or chosen here
    (SIMULATION_ENGINE_SPEC.md Section 6 remains undecided).
    """
    return ScenarioResult(
        subject="illustrative scenario: UK base rate -100bp -> UK Gilts impact",
        validation_status=ValidationStatus.PROVISIONAL,
        result="UK Gilts estimated to appreciate under a 100bp base rate cut",
        source="illustrative example — not a real data source",
        producer="simulation-engine (illustrative) / SIMULATION_ENGINE_SPEC.md Section 7",
        confidence=ConfidenceLevel.LOW,
        scenario_description="UK base rate: -100bp",
        affected_entity_id="entity:uk-gilts",
        base_case=0.028,
        range_low=-0.014,
        range_high=0.057,
        sensitivity_factors=[
            "GBP response — a weaker-than-expected currency reaction would "
            "reduce the estimated Gilt appreciation",
            "the extent to which the rate cut is already priced in by "
            "markets before it occurs",
        ],
        limitations=[
            "illustrative only — not derived from any real propagation "
            "process, historical data, or model",
        ],
    )
