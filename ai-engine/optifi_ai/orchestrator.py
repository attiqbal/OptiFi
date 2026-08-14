"""
CIOOrchestrator — Phase E6, the CIO/Manager synthesis entrypoint
(ENGINE_PIPELINE_SPECIFICATION.md Stage 12). Ties together every module in
this package: `intent.py` (routing), `roadblock.py` (staleness/missing
dependencies), `disagreement.py` (existing — disagreement recognition),
`verification_gate.py` (the REJECT-cannot-be-overridden gate),
`explanation.py` (Stage 13 structure).

`SpecialistOutputPool` stands in for what a live `backend` would eventually
assemble by calling specialist engine services over the network (the
*technical* orchestration `ENGINE_PIPELINE_SPECIFICATION.md` Section 11
assigns to `backend`, which remains a placeholder — see README.md). This
package builds no such service layer; `answer_query` below reasons over
whatever UAPs are already in the pool, exactly the boundary Section 11
draws. The two worked builder functions
(`build_simple_allocation_pool`/`build_complex_recession_pool`) populate a
pool by calling real specialist-engine functions directly and in-process —
the same pattern `replay-engine/optifi_replay/decision_package.py` (Phase
E5) already established, since nothing in this codebase is a live network
service; every "engine" is a local Python import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from optifi_causal import CausalClaim, TransmissionGraph
from optifi_forecast import exponential_smoothing_forecast
from optifi_optimisation import minimize_variance_with_loss_cap
from optifi_quant import covariance_matrix, estimate_factor_sensitivity, propagate_to_portfolio, SensitivityRegistry
from optifi_shared import (
    ConfidenceLevel,
    InformationClass,
    PortfolioAnalytics,
    UAP,
    ValidationStatus,
)
from optifi_simulation import propagate_scenario
from optifi_simulation.scenario_library import INFLATION_SURPRISE_1PP
from optifi_verification import check_no_look_ahead_contamination, verify_loss_cap_candidate, Verdict

from .disagreement import group_by_disagreement_set, has_genuine_disagreement
from .explanation import build_explanation, CIOExplanation, UserSophistication
from .generator import ExplanationGenerator
from .intent import classify_required_engines, RoutingDecision, SpecialistEngine
from .roadblock import check_staleness, detect_missing_dependencies, Roadblock
from .verification_gate import apply_gate, GateResult


@dataclass(frozen=True)
class UserQuery:
    """`text` is stored verbatim for audit and fed only to the routing
    heuristic (`intent.py`) — never treated as instructions to this
    orchestrator's own control flow. See `test_cio_adversarial.py` for
    the prompt-injection tests this is meant to survive: asking the CIO
    in plain text to "ignore the loss cap" or "just estimate the price"
    has no code path to actually do either."""

    text: str
    sophistication: UserSophistication = UserSophistication.INFORMED


@dataclass
class SpecialistOutputPool:
    """Already-produced UAPs, tagged by which specialist engine produced
    them. The CIO consumes this; it never produces a FACT/ESTIMATE UAP of
    its own to put into it."""

    by_engine: dict[SpecialistEngine, list[UAP]] = field(default_factory=dict)
    known_uaps: dict[str, UAP] = field(default_factory=dict)

    def add(self, engine: SpecialistEngine, uaps: list[UAP]) -> None:
        self.by_engine.setdefault(engine, []).extend(uaps)
        for uap in uaps:
            self.known_uaps[uap.id] = uap

    def available_engines(self) -> frozenset[SpecialistEngine]:
        return frozenset(engine for engine, uaps in self.by_engine.items() if uaps)

    def uaps_for(self, engines: frozenset[SpecialistEngine]) -> list[UAP]:
        result: list[UAP] = []
        for engine in engines:
            result.extend(self.by_engine.get(engine, []))
        return result


class CIOOrchestrator:
    def __init__(self, generator: ExplanationGenerator):
        self._generator = generator

    def answer_query(
        self,
        query: UserQuery,
        pool: SpecialistOutputPool,
        now: datetime,
        max_age: timedelta,
        candidate: UAP | None = None,
        candidate_verdicts: list[Verdict] | None = None,
    ) -> tuple[RoutingDecision, CIOExplanation]:
        routing = classify_required_engines(query.text)
        available = pool.available_engines()

        # VERIFICATION is handled via the explicit candidate/candidate_verdicts
        # path below, not as a pool-tagged UAP list (a Verdict is not a UAP) —
        # excluded here so it isn't double-reported as a missing dependency.
        pool_engines = routing.engines - {SpecialistEngine.VERIFICATION}
        roadblocks: list[Roadblock] = detect_missing_dependencies(pool_engines, available)
        relevant = pool.uaps_for(routing.engines)
        roadblocks += check_staleness(relevant, now, max_age)

        if SpecialistEngine.OPTIMISATION in routing.engines and candidate is None:
            roadblocks.append(
                Roadblock(
                    kind="MISSING_DEPENDENCY",
                    description=(
                        "OPTIMISATION was routed but no candidate was supplied to the "
                        "verification gate — a material recommendation must not be "
                        "synthesised without passing through verification-engine first"
                    ),
                    subject=SpecialistEngine.OPTIMISATION.value,
                )
            )

        groups = group_by_disagreement_set(relevant)
        disagreement_notes = [
            f"genuine disagreement in group '{ref}' across {len(group)} members "
            f"(values: {[u.result for u in group]}) — not resolved, only reported"
            for ref, group in groups.items()
            if has_genuine_disagreement(group)
        ]

        gate_result: GateResult | None = None
        if candidate is not None:
            if not candidate_verdicts:
                raise ValueError(
                    "answer_query: a candidate was supplied with no independent "
                    "verdicts. A material recommendation must not reach CIO "
                    "synthesis without having passed through verification-engine "
                    "first (Phase E6 'Verification Gate')."
                )
            gate_result = apply_gate(candidate_verdicts)
            if not gate_result.excluded and candidate.id not in pool.known_uaps:
                pool.known_uaps[candidate.id] = candidate

        explanation = build_explanation(
            relevant,
            disagreement_notes=disagreement_notes,
            roadblocks=roadblocks,
            candidate=candidate,
            gate_result=gate_result,
        )
        return routing, explanation


# === Worked example 1: simple lookup — "What is my technology allocation?" ===
#
# A pure retrieval: sector allocation from already-known holdings is Stage
# 8 (quant-engine) output — ENGINE_PIPELINE_SPECIFICATION.md Stage 8:
# "Directly-computed arithmetic from verified holdings... is FACT."
# Nothing here computes that arithmetic: this fixture represents output
# quant-engine has already produced upstream (illustrative, not real
# holdings), and `answer_query` only ever reasons over it — proving the
# "do not run every engine for every request" requirement by construction:
# no causal/forecast/simulation/optimisation call happens for this query.

_ILLUSTRATIVE_TECH_ALLOCATION = PortfolioAnalytics(
    metric_name="sector exposure", value=0.22, breakdown={"technology": 0.22, "other": 0.78}
)


def build_simple_allocation_pool(now: datetime) -> SpecialistOutputPool:
    pool = SpecialistOutputPool()
    allocation_uap = UAP(
        subject="portfolio sector allocation",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=_ILLUSTRATIVE_TECH_ALLOCATION,
        source="illustrative portfolio holdings — not a real user portfolio",
        producer="quant-engine (illustrative fixture — Stage 8 output already computed upstream)",
        confidence=ConfidenceLevel.HIGH,
        generated_at=now,
    )
    pool.add(SpecialistEngine.QUANT, [allocation_uap])
    return pool


# === Worked example 2: complex decision — "Should I reduce equities
# because recession risk has increased?" ===
#
# Full chain, real functions, same illustrative-not-real-data discipline
# replay-engine (Phase E5) established. Reuses simulation-engine's own
# INFLATION_SURPRISE_1PP scenario definition rather than inventing a new
# one.

_CPI_ENTITY = INFLATION_SURPRISE_1PP.perturbed_entity_id
_EQUITY_ENTITY = "entity:broad-equity-market"
# A second, low-volatility asset — only needed because covariance_matrix/
# minimize_variance_with_loss_cap require >=2 assets to have anything to
# optimise across; not itself scenario-propagated (Stage 7 only concerns
# the equity leg this query is actually about).
_CASH_LIKE_ENTITY = "entity:cash-like-asset"

# Small, fixed, illustrative synthetic series (not fitted to any real
# history) — long enough to satisfy estimate_factor_sensitivity's own
# minimum-observations floor.
_SYNTHETIC_CPI_HISTORY = [2.0, 2.3, 2.6, 2.9, 3.1, 3.4, 3.6, 3.8, 4.0, 4.1, 4.3, 4.5]
_SYNTHETIC_EQUITY_MONTHLY_RETURNS = [0.01, -0.02, 0.00, -0.03, -0.01, -0.04, -0.02, -0.05, -0.02, -0.04, -0.01, -0.03]
_SYNTHETIC_CASH_LIKE_RETURNS = [0.001] * 11

_DEFAULT_PORTFOLIO_WEIGHTS = {_EQUITY_ENTITY: 1.0}
_DEFAULT_MANDATE = {"portfolio_value": 250_000.0, "max_single_period_loss": 25_000.0, "confidence_level": 0.95}


def build_complex_recession_pool(
    now: datetime,
) -> tuple[SpecialistOutputPool, UAP, list[Verdict]]:
    """Returns (pool, optimisation_candidate, candidate_verdicts) — the
    shape `CIOOrchestrator.answer_query` expects. Runs causal-engine,
    forecast-engine, simulation-engine, quant-engine, optimisation-engine,
    and verification-engine's real functions, in that order, exactly the
    Phase E6 brief's own worked example
    (macro -> forecasting -> causal -> scenarios -> portfolio ->
    optimisation -> verification -> CIO)."""
    pool = SpecialistOutputPool()

    cpi_uaps = [
        UAP(
            subject="macro indicator: illustrative CPI YoY",
            information_class=InformationClass.FACT,
            validation_status=ValidationStatus.VERIFIED,
            result=value,
            source="illustrative synthetic fixture — not real data",
            producer="data-engine (illustrative fixture)",
            confidence=ConfidenceLevel.MODERATE,
            generated_at=now,
        )
        for value in _SYNTHETIC_CPI_HISTORY
    ]
    pool.add(SpecialistEngine.DATA, cpi_uaps)

    # === Forecast (Stage 6) ===
    forecast_value = exponential_smoothing_forecast(_SYNTHETIC_CPI_HISTORY)
    forecast_uap = UAP(
        subject="illustrative CPI YoY — 1-period-ahead forecast",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=forecast_value,
        source="computed from the illustrative CPI history above",
        producer="forecast-engine / exponential_smoothing_forecast",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=[u.id for u in cpi_uaps],
        provenance_chain=[u.id for u in cpi_uaps],
        generated_at=now,
    )
    pool.add(SpecialistEngine.FORECAST, [forecast_uap])

    # === Causal pathway + sensitivity (Stage 5) ===
    graph = TransmissionGraph()
    causal_claim = CausalClaim(
        subject="CPI surprise -> broad equity market",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A CPI surprise raises discount-rate expectations, pressuring equity valuations",
        source="illustrative — not a real data source",
        producer="causal-engine (illustrative)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=_CPI_ENTITY,
        effect_entity_id=_EQUITY_ENTITY,
        mechanism="Higher inflation raises discount rates applied to future cash flows.",
        publication_time=now,
        retrieval_time=now,
    )
    graph.add_edges([causal_claim])
    pool.add(SpecialistEngine.CAUSAL, [causal_claim])

    registry = SensitivityRegistry()
    cpi_changes = [b - a for a, b in zip(_SYNTHETIC_CPI_HISTORY, _SYNTHETIC_CPI_HISTORY[1:])]
    equity_sensitivity = estimate_factor_sensitivity(
        _CPI_ENTITY,
        _EQUITY_ENTITY,
        cpi_changes,
        _SYNTHETIC_EQUITY_MONTHLY_RETURNS[: len(cpi_changes)],
        horizon=INFLATION_SURPRISE_1PP.horizon,
        regime=None,
        min_observations=min(11, len(cpi_changes)),
    ).model_copy(update={"publication_time": now, "retrieval_time": now})
    registry.register(_CPI_ENTITY, _EQUITY_ENTITY, equity_sensitivity)

    # === Scenario propagation (Stage 7) ===
    scenario_result = propagate_scenario(
        INFLATION_SURPRISE_1PP, _EQUITY_ENTITY, graph, registry, _CPI_ENTITY, as_of=now
    )
    pool.add(SpecialistEngine.SIMULATION, [scenario_result])

    # === Portfolio propagation (Stage 8) ===
    portfolio_impact = propagate_to_portfolio([scenario_result], _DEFAULT_PORTFOLIO_WEIGHTS)
    pool.add(SpecialistEngine.QUANT, [portfolio_impact])

    # === Optimisation (Stage 9) — baseline expected returns/covariance,
    # deliberately not the scenario's own stressed figures (same
    # discipline replay-engine's decision_package.py documents). Uses both
    # illustrative assets — covariance_matrix requires at least two. ===
    equity_returns = _SYNTHETIC_EQUITY_MONTHLY_RETURNS[: len(_SYNTHETIC_CASH_LIKE_RETURNS)]
    cov_uap = covariance_matrix(
        {_EQUITY_ENTITY: equity_returns, _CASH_LIKE_ENTITY: _SYNTHETIC_CASH_LIKE_RETURNS}
    )
    expected_returns = {
        _EQUITY_ENTITY: sum(equity_returns) / len(equity_returns),
        _CASH_LIKE_ENTITY: sum(_SYNTHETIC_CASH_LIKE_RETURNS) / len(_SYNTHETIC_CASH_LIKE_RETURNS),
    }
    target_return = sum(expected_returns.values()) / len(expected_returns)

    optimisation_candidate = minimize_variance_with_loss_cap(
        expected_returns=expected_returns,
        covariance=cov_uap.result,
        target_return=target_return,
        portfolio_value=_DEFAULT_MANDATE["portfolio_value"],
        max_single_period_loss=_DEFAULT_MANDATE["max_single_period_loss"],
        confidence_level=_DEFAULT_MANDATE["confidence_level"],
        covariance_source_id=cov_uap.id,
    )

    # === Verification (Stage 11) — CIO Responsibility #9: sent to
    # verification before this candidate is ever handed to answer_query ===
    loss_cap_verdict = verify_loss_cap_candidate(
        weights=optimisation_candidate.result["weights"],
        expected_returns=expected_returns,
        covariance=cov_uap.result,
        target_return=target_return,
        portfolio_value=_DEFAULT_MANDATE["portfolio_value"],
        max_single_period_loss=_DEFAULT_MANDATE["max_single_period_loss"],
        confidence_level=_DEFAULT_MANDATE["confidence_level"],
        min_weight=0.0,
        max_weight=1.0,
    )
    known_packets = dict(pool.known_uaps)
    known_packets[optimisation_candidate.id] = optimisation_candidate
    no_look_ahead_verdict = check_no_look_ahead_contamination(scenario_result, known_packets)

    pool.add(SpecialistEngine.OPTIMISATION, [optimisation_candidate])

    return pool, optimisation_candidate, [loss_cap_verdict, no_look_ahead_verdict]
