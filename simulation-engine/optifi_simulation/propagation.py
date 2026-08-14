"""
Scenario propagation — PHASE E4 brief, Parts 1/2/3/4/5: the actual
transmission from "what if this state occurs" (a `ScenarioDefinition`)
to "how might this asset react" (a `ScenarioResult`), genuinely computed
from `causal-engine`'s transmission graph and `quant-engine`'s
empirical/deterministic sensitivities — "no hand-authored arbitrary
return numbers should survive as production analytical logic."

Two things are checked before any number is computed, each a distinct,
separately-tested failure mode:

1. A supported causal PATHWAY must exist from the scenario's perturbed
   entity to the target asset (`TransmissionGraph.require_pathway` —
   raises `UnsupportedFailure`, Testing Requirement "unsupported asset").
   This is the QUALITATIVE check: is there evidence this scenario
   affects this asset at all?
2. A registered sensitivity must quantify `(sensitivity_factor_id,
   target_entity_id)` (`SensitivityRegistry.get_sensitivity` — raises
   `MissingInputFailure` for "missing factor exposure",
   `OutOfDistributionFailure` for "regime mismatch",
   `ConflictedInputFailure` via `.single()` for "conflicting
   asset-response models"). This is the QUANTITATIVE check: how much,
   and is that figure trustworthy under the requested regime?

`sensitivity_factor_id` is deliberately a separate parameter from the
scenario's own `perturbed_entity_id` — the causal pathway proves *some*
evidenced chain connects the scenario to the asset (e.g. inflation
surprise -> policy-rate expectations -> yield curve -> duration-sensitive
assets), but the empirically/deterministically MEASURABLE sensitivity
typically attaches to the pathway's last, most directly observable hop
(e.g. yield curve -> the asset), not the scenario's original driver
several hops upstream. Composing sensitivities across multiple hops into
one end-to-end figure is a genuinely harder, unresolved problem — see
the Phase E4 deliverable's open research questions — this module does
not silently invent an answer to it.
"""

from __future__ import annotations

from datetime import datetime

from optifi_causal import TransmissionGraph
from optifi_quant import SensitivityRegistry
from optifi_shared import ConfidenceLevel, UnsupportedFailure

from .scenario_library import ScenarioDefinition
from .scenario_result import ScenarioResult

# Unit -> decimal-fraction conversion. A small, explicit, documented
# convention (not a general unit-algebra system) — "no hand-authored
# arbitrary return numbers" refers to SCENARIO IMPACT figures, not this
# kind of fixed, standard unit definition (100 basis points IS 1% by
# definition, not a modelling choice).
_UNIT_TO_DECIMAL = {
    "bps": 1 / 10_000,
    "pp": 1 / 100,
    "%": 1 / 100,
}

# Deterministic sensitivities (e.g. bond duration) carry no sampling
# distribution to derive a confidence interval from — this fixed
# fractional half-width around the point estimate is a documented,
# simple placeholder for "some genuine uncertainty must be expressed"
# (Part 5), not a calibrated figure. Flagged in the deliverable's open
# questions as needing real calibration.
_DETERMINISTIC_UNCERTAINTY_FRACTION = 0.25

# Statistical sensitivities' range uses beta's own standard error
# (`factor_sensitivity.py`'s real OLS computation) at this z-multiplier —
# 1.96 approximates a 95% confidence interval under a normality
# assumption, the standard convention, not a value invented here.
_STATISTICAL_CONFIDENCE_Z = 1.96

# Safety floor: guarantees a genuinely non-zero range width even in a
# pathological edge case (e.g. r_squared so close to 1 that the computed
# half-width rounds to zero) — ScenarioResult's own guardrail (Phase E4)
# would otherwise reject the result outright for expressing no
# uncertainty at all, which is worse than a small floored width.
_MIN_RANGE_HALF_WIDTH_FRACTION = 1e-6


def _to_decimal_fraction(magnitude: float, unit: str) -> float:
    if unit not in _UNIT_TO_DECIMAL:
        raise UnsupportedFailure(
            f"_to_decimal_fraction: unit {unit!r} is not a recognised scenario "
            f"unit (known: {sorted(_UNIT_TO_DECIMAL)!r}) — refusing to guess a "
            "conversion factor rather than silently mis-scaling the impact."
        )
    return magnitude * _UNIT_TO_DECIMAL[unit]


def propagate_scenario(
    scenario: ScenarioDefinition,
    target_entity_id: str,
    transmission_graph: TransmissionGraph,
    sensitivity_registry: SensitivityRegistry,
    sensitivity_factor_id: str,
    regime: str | None = None,
    as_of: datetime | None = None,
) -> ScenarioResult:
    """
    Propagates `scenario` to `target_entity_id`, returning a real,
    computed `ScenarioResult` — never a hand-picked base_case/range.
    """
    pathways = transmission_graph.require_pathway(scenario.perturbed_entity_id, target_entity_id)

    lookup = sensitivity_registry.get_sensitivity(sensitivity_factor_id, target_entity_id, regime=regime)
    sensitivity_uap = lookup.single()

    sensitivity_horizon = sensitivity_uap.result.get("horizon")
    if sensitivity_horizon is not None and sensitivity_horizon != scenario.horizon:
        raise UnsupportedFailure(
            f"propagate_scenario: scenario {scenario.scenario_id!r} has horizon "
            f"{scenario.horizon!r}, but the sensitivity estimate for "
            f"({sensitivity_factor_id!r}, {target_entity_id!r}) was computed "
            f"over horizon {sensitivity_horizon!r} — a sensitivity estimated "
            "at one horizon is not assumed valid at another without an "
            "explicit, justified reason this project does not invent here."
        )

    perturbation_decimal = _to_decimal_fraction(scenario.perturbation_magnitude, scenario.unit)
    beta = sensitivity_uap.result["sensitivity"]
    method = sensitivity_uap.result["method"]

    base_case = beta * perturbation_decimal

    if method == "statistical-ols":
        standard_error = sensitivity_uap.result["standard_error"]
        half_width_beta = _STATISTICAL_CONFIDENCE_Z * standard_error
    else:
        half_width_beta = abs(beta) * _DETERMINISTIC_UNCERTAINTY_FRACTION

    bound_a = (beta - half_width_beta) * perturbation_decimal
    bound_b = (beta + half_width_beta) * perturbation_decimal
    range_low, range_high = min(bound_a, bound_b), max(bound_a, bound_b)

    if range_high - range_low < _MIN_RANGE_HALF_WIDTH_FRACTION:
        floor = max(abs(base_case), 1.0) * _MIN_RANGE_HALF_WIDTH_FRACTION
        range_low, range_high = base_case - floor, base_case + floor

    # `range` must strictly contain `base_case` per ScenarioResult's own
    # guardrail — guaranteed by construction here (bound_a/bound_b
    # straddle beta*perturbation symmetrically), but floating point can
    # occasionally place base_case exactly on a boundary; widen minutely
    # rather than let a razor-thin numerical edge case fail construction.
    if not (range_low < base_case < range_high):
        range_low, range_high = min(range_low, base_case) - 1e-9, max(range_high, base_case) + 1e-9

    regime_note = f"regime: {regime}" if regime else "regime-unconditional"
    fallback_note = (
        "regime-agnostic fallback used (no estimate specific to the requested regime exists)"
        if lookup.fallback_used
        else "regime-specific estimate" if regime else "regime-agnostic estimate"
    )
    sensitivity_factors = [
        f"sensitivity of {target_entity_id} to {sensitivity_factor_id} ({method})",
        regime_note,
        fallback_note,
    ]
    if method == "statistical-ols":
        sensitivity_factors.append(
            f"r_squared={sensitivity_uap.result['r_squared']:.3f} on "
            f"{sensitivity_uap.result['n_observations']} observations"
        )

    limitations = [
        "impact is a first-order (linear) approximation: sensitivity x perturbation, "
        "not a full structural or general-equilibrium model",
        "the causal pathway establishes a supported transmission mechanism exists; "
        "it does not itself certify the sensitivity's magnitude — that comes solely "
        "from the registered sensitivity estimate",
    ]
    if lookup.fallback_used:
        limitations.append(
            f"no sensitivity estimate specific to regime {regime!r} was available — "
            "the regime-agnostic estimate was used instead, which may understate "
            "how conditional the true relationship is on the current regime"
        )
    if method != "statistical-ols":
        limitations.append(
            f"range width uses a fixed {_DETERMINISTIC_UNCERTAINTY_FRACTION:.0%} "
            "heuristic around the deterministic point estimate, not a calibrated "
            "confidence interval (deterministic relationships carry no sampling "
            "distribution to derive one from)"
        )

    dependencies = [sensitivity_uap.id] + [edge.id for pathway in pathways for edge in pathway.edges]

    return ScenarioResult(
        subject=f"scenario: {scenario.description} -> {target_entity_id}",
        validation_status=sensitivity_uap.validation_status,
        result=(
            f"Under scenario '{scenario.description}', {target_entity_id} is estimated "
            f"to move {base_case:+.4%} (range {range_low:+.4%} to {range_high:+.4%})"
        ),
        source=f"computed via causal transmission pathway + {method} sensitivity",
        producer="simulation-engine / propagate_scenario, PHASE E4 Part 2/3",
        confidence=ConfidenceLevel.LOW if lookup.fallback_used else sensitivity_uap.confidence,
        scenario_description=scenario.description,
        affected_entity_id=target_entity_id,
        base_case=base_case,
        range_low=range_low,
        range_high=range_high,
        sensitivity_factors=sensitivity_factors,
        limitations=limitations,
        dependencies=dependencies,
        provenance_chain=dependencies,
        as_of=as_of,
    )
