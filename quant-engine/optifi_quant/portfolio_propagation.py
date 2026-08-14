"""
Portfolio propagation — PHASE E4 brief, Part 7: "Translate scenario
results through: holdings; asset weights..." and Stage 8's own role
(SIMULATION_ENGINE_SPEC.md Section 3: "`quant-engine` applies [scenario-
conditional, asset-class-level] output to a specific user's actual
portfolio composition, producing the personalised portfolio-level impact
figure").

Deliberately generic across dimensions rather than seven bespoke
functions (currency, sector, duration, factor, concentration,
liquidity): `propagate_to_portfolio` takes ANY `entity_id -> weight`
mapping and any matching set of scenario results — call it once with
per-holding weights against per-asset `ScenarioResult`s, again with
sector weights against per-sector results, again with currency-exposure
weights against per-currency results. One well-tested primitive, reused
across dimensions, rather than fabricating superficial per-dimension
specificity this phase does not actually need. Concentration (HHI) and a
genuine multi-style factor-exposure model are NOT implemented here — see
the Phase E4 deliverable's open questions; QUANT_ENGINE_SPEC.md Section
11 item 4 already leaves the style-factor-model choice open, and this
module does not silently resolve it.

`scenario_results` is typed as `list[UAP]`, not `list[ScenarioResult]`,
DELIBERATELY: `simulation-engine` already depends on `quant-engine` (for
`SensitivityRegistry`/`estimate_factor_sensitivity`, Stage 7 consuming
Stage 8's sensitivity tools per Part 3); importing `ScenarioResult` back
into `quant-engine` would create a circular PACKAGE dependency. Each
element is expected to structurally have `.affected_entity_id`,
`.base_case`, `.range_low`, `.range_high` — true of any real
`ScenarioResult` (a `UAP` subclass, so plain attribute access works
without this package needing to import that specific class) — validated
explicitly at runtime rather than silently assumed.
"""

from __future__ import annotations

from optifi_shared import (
    ConfidenceLevel,
    InformationClass,
    propagate_validation_status,
    UAP,
    UnsupportedFailure,
    ValidationStatus,
)

_WEIGHTS_SUM_TOLERANCE = 1e-6
_REQUIRED_SCENARIO_RESULT_ATTRS = ("affected_entity_id", "base_case", "range_low", "range_high")
_CONFIDENCE_RANK = {ConfidenceLevel.LOW: 0, ConfidenceLevel.MODERATE: 1, ConfidenceLevel.HIGH: 2}


def _worst_confidence(uaps: list[UAP]) -> ConfidenceLevel:
    """No shared utility for this exists yet (`validation_propagation.py`
    only covers `validation_status`) — same 'never silently better than
    the worst upstream input' principle, applied to `confidence` here
    locally rather than assumed."""
    return min((uap.confidence for uap in uaps), key=lambda c: _CONFIDENCE_RANK[c])


def _validate_scenario_result_shape(uap: UAP) -> None:
    missing = [attr for attr in _REQUIRED_SCENARIO_RESULT_ATTRS if not hasattr(uap, attr)]
    if missing:
        identity = getattr(uap, "id", repr(uap))
        raise TypeError(
            f"propagate_to_portfolio: object {identity!r} is missing "
            f"{missing!r} — expected a ScenarioResult-shaped UAP "
            "(affected_entity_id/base_case/range_low/range_high)."
        )


def propagate_to_portfolio(scenario_results: list[UAP], holdings: dict[str, float]) -> UAP:
    """
    `holdings`: `entity_id -> weight`, weights summing to 1.0 (within
    tolerance) — the same convention `portfolio_variance` already uses.

    Raises `UnsupportedFailure` (Testing Requirement "unsupported
    asset") if a holding has no matching scenario result — never
    silently treats a missing entity as zero impact.
    """
    if not holdings:
        raise ValueError("propagate_to_portfolio: holdings must not be empty.")
    weight_sum = sum(holdings.values())
    if abs(weight_sum - 1.0) > _WEIGHTS_SUM_TOLERANCE:
        raise ValueError(
            f"propagate_to_portfolio: holdings weights must sum to 1.0 within "
            f"a tolerance of {_WEIGHTS_SUM_TOLERANCE}; got sum={weight_sum!r}."
        )

    for sr in scenario_results:
        _validate_scenario_result_shape(sr)
    by_entity: dict[str, UAP] = {}
    for sr in scenario_results:
        by_entity.setdefault(sr.affected_entity_id, sr)  # first match wins if duplicated; see limitations note

    missing_entities = [entity_id for entity_id in holdings if entity_id not in by_entity]
    if missing_entities:
        raise UnsupportedFailure(
            f"propagate_to_portfolio: no scenario result covers holding(s) "
            f"{missing_entities!r} — this project never fabricates a zero-impact "
            "assumption for an asset the scenario simply wasn't propagated to."
        )

    contributions: dict[str, dict] = {}
    portfolio_base_case = 0.0
    portfolio_range_low = 0.0
    portfolio_range_high = 0.0
    for entity_id, weight in holdings.items():
        sr = by_entity[entity_id]
        weighted_base = weight * sr.base_case
        contributions[entity_id] = {
            "weight": weight,
            "base_case": sr.base_case,
            "range_low": sr.range_low,
            "range_high": sr.range_high,
            "weighted_contribution": weighted_base,
        }
        portfolio_base_case += weighted_base
        # Naive linear combination — see limitations. Documented
        # simplification, not a claim of joint-distribution rigor.
        portfolio_range_low += weight * sr.range_low
        portfolio_range_high += weight * sr.range_high

    sorted_contributions = dict(
        sorted(contributions.items(), key=lambda kv: abs(kv[1]["weighted_contribution"]), reverse=True)
    )

    contributing_uaps = [by_entity[entity_id] for entity_id in holdings]
    portfolio_validation_status = propagate_validation_status(ValidationStatus.PROVISIONAL, contributing_uaps)
    portfolio_confidence = _worst_confidence(contributing_uaps)

    return UAP(
        subject=f"portfolio scenario impact: {', '.join(sorted(holdings))}",
        information_class=InformationClass.ESTIMATE,
        validation_status=portfolio_validation_status,
        result={
            "portfolio_base_case": portfolio_base_case,
            "range_low": portfolio_range_low,
            "range_high": portfolio_range_high,
            "contributions": sorted_contributions,
        },
        source="computed from the provided per-holding scenario results and weights",
        producer="quant-engine / propagate_to_portfolio, PHASE E4 Part 7",
        confidence=portfolio_confidence,
        assumptions=[
            "holdings weights sum to 1.0 (or the invested proportion, if cash "
            "is held out separately) and reference the same entity_id "
            "convention the scenario results use",
        ],
        limitations=[
            "portfolio-level range is a WEIGHTED SUM of each holding's own "
            "range bounds — this implicitly assumes every holding's worst "
            "(or best) case occurs simultaneously, which overstates portfolio "
            "range width whenever holdings are not perfectly correlated. A "
            "rigorous joint/Monte-Carlo combination using the holdings' actual "
            "covariance structure is a genuinely harder problem this "
            "function does not attempt (see the Phase E4 deliverable's open "
            "questions) — this is a documented, honest MVP simplification, "
            "not a claim of statistical rigor",
            "each contributing scenario result's own limitations (regime "
            "fallback, linear approximation, sample size, etc.) propagate "
            "through to this portfolio-level figure but are not re-stated "
            "here individually — see `dependencies` and each scenario "
            "result's own `limitations`",
            "if more than one scenario result was supplied for the same "
            "affected_entity_id, only the first is used — competing scenario "
            "results for the same asset are not reconciled here; the caller "
            "is responsible for resolving that disagreement before calling "
            "this function",
        ],
        dependencies=[sr.id for sr in by_entity.values() if sr.affected_entity_id in holdings],
    )
