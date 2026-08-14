"""
HistoricalDecisionPackage — PHASE E5 brief, Part 2 ("Replay Workflow"):
freeze the information universe, then run the normal OptiFi pipeline —
forecast, scenario, portfolio analysis, optimisation, verification —
producing one immutable, storable record.

`run_replay` orchestrates ONLY: it calls real, already-existing,
unmodified functions from `causal-engine`, `forecast-engine`,
`evaluation-engine`, `simulation-engine`, `quant-engine`,
`optimisation-engine`, and `verification-engine`, in sequence, on data
that has already passed through `build_snapshot`'s freeze. It
implements no analytical methodology of its own.

Two things are DELIBERATELY kept separate, per Part 1's own instruction
elsewhere in this brief that forecast/scenario/asset-response concepts
must not be conflated, extended here to optimisation: the OPTIMISATION
step's `expected_returns`/covariance describe NORMAL, historical,
steady-state asset behaviour (a baseline), while the SCENARIO step's
`base_case`/range describe a stressed, hypothetical WHAT-IF. Reusing the
scenario's stressed figures as the optimiser's baseline assumption would
conflate "what usually happens" with "what happens if this shock
occurs" — two different questions this project keeps structurally
distinct throughout (Stage 6/7 vs. Stage 9).

Scope, stated honestly: this reconstructs Stages 5 (causal) through 11
(verification) — it does NOT reconstruct Stage 3/10/12/13 (AI-engine
candidate framing / CIO synthesis), since `ai-engine` itself has no real
LLM integration to reconstruct (only `StubExplanationGenerator` exists —
see `ai-engine/README.md`); attempting to "replay" a stub would not be a
genuine historical reconstruction of anything. This is a real, current
gap, not glossed over — see the Phase E5 deliverable's own limitations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from optifi_causal import CausalClaim, TransmissionGraph
from optifi_evaluation import ForecastKind, ForecastRecord
from optifi_forecast import exponential_smoothing_forecast
from optifi_optimisation import minimize_variance_with_loss_cap
from optifi_quant import (
    covariance_matrix,
    duration_price_sensitivity,
    estimate_factor_sensitivity,
    propagate_to_portfolio,
    SensitivityRegistry,
)
from optifi_shared import (
    ConfidenceLevel,
    InformationClass,
    MacroObservation,
    MarketObservation,
    UAP,
    ValidationStatus,
)
from optifi_simulation import propagate_scenario
from optifi_simulation.scenario_library import INFLATION_SURPRISE_1PP
from optifi_verification import check_no_look_ahead_contamination, verify_loss_cap_candidate, Verdict

from .historical_periods import day_offset_date, HistoricalPeriod, month_offset_date
from .snapshot import build_snapshot, HistoricalSnapshot

CPI_ENTITY = INFLATION_SURPRISE_1PP.perturbed_entity_id  # "entity:uk-cpi-yoy"
DURATION_ASSET_ENTITY = "entity:duration-sensitive-assets"
EQUITY_ASSET_ENTITY = "entity:broad-equity-market"

MODIFIED_DURATION = 7.0
DEFAULT_PORTFOLIO_WEIGHTS = {DURATION_ASSET_ENTITY: 0.5, EQUITY_ASSET_ENTITY: 0.5}
DEFAULT_MANDATE = {
    "portfolio_value": 500_000.0,
    "max_single_period_loss": 50_000.0,
    "confidence_level": 0.95,
}
INDEX_RETURNS_MONTH_LENGTH = 21  # trading days per synthetic month bucket


def _macro_observation_uaps(period: HistoricalPeriod) -> list[UAP]:
    """One MacroObservation UAP per month of the FULL series — including
    months after `as_of` deliberately, so `build_snapshot`'s own
    filtering is genuinely exercised, not bypassed by a caller who
    pre-filtered."""
    series = period.cpi_series()
    uaps = []
    for i, value in enumerate(series):
        t = month_offset_date(i)
        uaps.append(
            UAP(
                subject="macro indicator: replay CPI YoY",
                information_class=InformationClass.FACT,
                validation_status=ValidationStatus.VERIFIED,
                result=MacroObservation(indicator_name="replay CPI YoY", value=value, unit="%"),
                source="synthetic replay fixture — not real data",
                producer=f"replay-engine / historical_periods ({period.period_id})",
                confidence=ConfidenceLevel.MODERATE,
                observation_time=t,
                publication_time=t,
                retrieval_time=t,
            )
        )
    return uaps


def _market_observation_uaps(period: HistoricalPeriod) -> list[UAP]:
    """One MarketObservation UAP per trading day, `price` a cumulative
    index level (base 100) built from the period's daily returns — a
    real price series, not raw returns stuffed into the wrong field."""
    levels = period.index_price_levels()
    uaps = []
    for i, level in enumerate(levels):
        t = day_offset_date(i)
        uaps.append(
            UAP(
                subject="market price: replay broad index",
                information_class=InformationClass.FACT,
                validation_status=ValidationStatus.VERIFIED,
                result=MarketObservation(instrument_id="REPLAY_INDEX", price=level, currency="GBP"),
                source="synthetic replay fixture — not real data",
                producer=f"replay-engine / historical_periods ({period.period_id})",
                confidence=ConfidenceLevel.MODERATE,
                observation_time=t,
                publication_time=t,
                retrieval_time=t,
            )
        )
    return uaps


def _ordered_macro_values(snapshot: HistoricalSnapshot) -> tuple[list[float], list[UAP]]:
    macro_uaps = sorted(
        (u for u in snapshot.available_uaps if isinstance(u.result, MacroObservation)),
        key=lambda u: u.observation_time,
    )
    return [u.result.value for u in macro_uaps], macro_uaps


def _ordered_market_prices(snapshot: HistoricalSnapshot) -> tuple[list[float], list[UAP]]:
    market_uaps = sorted(
        (u for u in snapshot.available_uaps if isinstance(u.result, MarketObservation)),
        key=lambda u: u.observation_time,
    )
    return [u.result.price for u in market_uaps], market_uaps


def _monthly_bucket_returns(daily_prices: list[float], bucket_size: int = INDEX_RETURNS_MONTH_LENGTH) -> list[float]:
    """Non-overlapping bucket returns from a price level series — same
    'drop the trailing partial window' discipline as forecast-engine's
    own `realised_volatility_series` (Phase E3)."""
    n_buckets = len(daily_prices) // bucket_size
    returns = []
    for i in range(n_buckets):
        start_price = daily_prices[i * bucket_size]
        end_price = daily_prices[(i + 1) * bucket_size - 1]
        returns.append((end_price - start_price) / start_price)
    return returns


@dataclass(frozen=True)
class HistoricalDecisionPackage:
    period_id: str
    as_of: datetime
    snapshot: HistoricalSnapshot
    forecast_uap: UAP
    forecast_record: ForecastRecord
    scenario_results: dict[str, UAP]
    portfolio_impact: UAP
    optimisation_candidate: UAP
    verification_verdicts: dict[str, Verdict]
    generated_at: datetime


def run_replay(
    period: HistoricalPeriod,
    portfolio_weights: dict[str, float] | None = None,
    mandate: dict | None = None,
) -> HistoricalDecisionPackage:
    portfolio_weights = portfolio_weights or DEFAULT_PORTFOLIO_WEIGHTS
    mandate = mandate or DEFAULT_MANDATE
    as_of = period.as_of

    # === Freeze (Part 1/2) ===
    candidate_uaps = _macro_observation_uaps(period) + _market_observation_uaps(period)
    snapshot = build_snapshot(as_of, candidate_uaps, portfolio=portfolio_weights, mandate=mandate)

    cpi_values, cpi_uaps = _ordered_macro_values(snapshot)
    market_prices, _ = _ordered_market_prices(snapshot)

    # === Forecast (Stage 6) ===
    forecast_value = exponential_smoothing_forecast(cpi_values)
    forecast_uap = UAP(
        subject=INFLATION_SURPRISE_1PP.description + " — 1-month-ahead CPI forecast",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=forecast_value,
        source="computed from the frozen historical snapshot's available CPI history",
        producer="replay-engine / exponential_smoothing_forecast, PHASE E5",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=[u.id for u in cpi_uaps],
        provenance_chain=[u.id for u in cpi_uaps],
        as_of=as_of,
    )
    forecast_record = ForecastRecord(
        forecast_packet_id=forecast_uap.id,
        target="replay CPI YoY, 1-month horizon",
        forecast_timestamp=as_of,
        horizon="1-month",
        forecast_kind=ForecastKind.POINT,
        predicted_point=forecast_value,
        model_id="econometric-ses",
        model_version="v1",
    )

    # === Causal pathways + sensitivities (Stage 5, Part 3 of PHASE E4) ===
    graph = TransmissionGraph()
    causal_duration = CausalClaim(
        subject="CPI surprise -> duration-sensitive assets",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A CPI surprise shifts rate expectations, which moves yields and duration-sensitive asset prices",
        source="illustrative — not a real data source",
        producer="replay-engine (illustrative)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=CPI_ENTITY,
        effect_entity_id=DURATION_ASSET_ENTITY,
        mechanism="Higher inflation raises policy-rate expectations, which raises yields; duration-sensitive asset prices move inversely to yields.",
        regime=period.regime_label,
        publication_time=month_offset_date(0),
        retrieval_time=month_offset_date(0),
    )
    causal_equity = CausalClaim(
        subject="CPI surprise -> broad equity market",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A CPI surprise affects discount rates and growth expectations, moving broad equity valuations",
        source="illustrative — not a real data source",
        producer="replay-engine (illustrative)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=CPI_ENTITY,
        effect_entity_id=EQUITY_ASSET_ENTITY,
        mechanism="Higher inflation raises discount rates applied to future cash flows, pressuring equity valuations.",
        regime=period.regime_label,
        publication_time=month_offset_date(0),
        retrieval_time=month_offset_date(0),
    )
    graph.add_edges([causal_duration, causal_equity])

    cpi_changes = [b - a for a, b in zip(cpi_values, cpi_values[1:])]
    equity_monthly_returns = _monthly_bucket_returns(market_prices)
    n = min(len(cpi_changes), len(equity_monthly_returns))
    cpi_changes, equity_monthly_returns = cpi_changes[:n], equity_monthly_returns[:n]

    registry = SensitivityRegistry()
    duration_sensitivity = duration_price_sensitivity(modified_duration=MODIFIED_DURATION)
    duration_sensitivity = duration_sensitivity.model_copy(
        update={
            "result": {**duration_sensitivity.result, "horizon": INFLATION_SURPRISE_1PP.horizon, "regime": None},
            # A deterministic formula "becomes known" the moment it's
            # computed from already-available inputs — dated at the
            # same point as the causal claims above for consistency,
            # so the look-ahead check can verify it (not just tolerate
            # it as unverifiable) rather than for any deeper reason.
            "publication_time": month_offset_date(0),
            "retrieval_time": month_offset_date(0),
        }
    )
    registry.register(CPI_ENTITY, DURATION_ASSET_ENTITY, duration_sensitivity)

    equity_sensitivity = estimate_factor_sensitivity(
        CPI_ENTITY,
        EQUITY_ASSET_ENTITY,
        cpi_changes,
        equity_monthly_returns,
        horizon=INFLATION_SURPRISE_1PP.horizon,
        regime=None,
        min_observations=min(12, max(3, n)),
    )
    # Unlike the deterministic sensitivity above, this one is only
    # genuinely known once its own last input observation is available
    # — dated at the as_of cutoff itself (it was estimated using data
    # available AT T, not before).
    equity_sensitivity = equity_sensitivity.model_copy(
        update={"publication_time": as_of, "retrieval_time": as_of}
    )
    registry.register(CPI_ENTITY, EQUITY_ASSET_ENTITY, equity_sensitivity)

    # === Scenario propagation (Stage 7) ===
    scenario_results = {
        DURATION_ASSET_ENTITY: propagate_scenario(
            INFLATION_SURPRISE_1PP, DURATION_ASSET_ENTITY, graph, registry, CPI_ENTITY, as_of=as_of
        ),
        EQUITY_ASSET_ENTITY: propagate_scenario(
            INFLATION_SURPRISE_1PP, EQUITY_ASSET_ENTITY, graph, registry, CPI_ENTITY, as_of=as_of
        ),
    }

    # === Portfolio propagation (Stage 8) ===
    portfolio_impact = propagate_to_portfolio(list(scenario_results.values()), portfolio_weights)

    # === Optimisation (Stage 9) — baseline expected returns/covariance,
    # === deliberately NOT the scenario's stressed figures (see module docstring) ===
    bond_baseline_returns = [-MODIFIED_DURATION * (c / 100.0) for c in cpi_changes]
    cov_uap = covariance_matrix(
        {DURATION_ASSET_ENTITY: bond_baseline_returns, EQUITY_ASSET_ENTITY: equity_monthly_returns}
    )
    expected_returns = {
        DURATION_ASSET_ENTITY: sum(bond_baseline_returns) / len(bond_baseline_returns),
        EQUITY_ASSET_ENTITY: sum(equity_monthly_returns) / len(equity_monthly_returns),
    }
    target_return = sum(expected_returns.values()) / len(expected_returns)

    optimisation_candidate = minimize_variance_with_loss_cap(
        expected_returns=expected_returns,
        covariance=cov_uap.result,
        target_return=target_return,
        portfolio_value=mandate["portfolio_value"],
        max_single_period_loss=mandate["max_single_period_loss"],
        confidence_level=mandate["confidence_level"],
        covariance_source_id=cov_uap.id,
    )

    # === Verification (Stage 11) ===
    loss_cap_verdict = verify_loss_cap_candidate(
        weights=optimisation_candidate.result["weights"],
        expected_returns=expected_returns,
        covariance=cov_uap.result,
        target_return=target_return,
        portfolio_value=mandate["portfolio_value"],
        max_single_period_loss=mandate["max_single_period_loss"],
        confidence_level=mandate["confidence_level"],
        min_weight=0.0,
        max_weight=1.0,
    )

    known_packets = {u.id: u for u in snapshot.available_uaps}
    known_packets[causal_duration.id] = causal_duration
    known_packets[causal_equity.id] = causal_equity
    known_packets[duration_sensitivity.id] = duration_sensitivity
    known_packets[equity_sensitivity.id] = equity_sensitivity

    verification_verdicts = {
        "loss_cap": loss_cap_verdict,
        "forecast_no_look_ahead": check_no_look_ahead_contamination(forecast_uap, known_packets),
        "duration_scenario_no_look_ahead": check_no_look_ahead_contamination(
            scenario_results[DURATION_ASSET_ENTITY], known_packets
        ),
        "equity_scenario_no_look_ahead": check_no_look_ahead_contamination(
            scenario_results[EQUITY_ASSET_ENTITY], known_packets
        ),
    }

    return HistoricalDecisionPackage(
        period_id=period.period_id,
        as_of=as_of,
        snapshot=snapshot,
        forecast_uap=forecast_uap,
        forecast_record=forecast_record,
        scenario_results=scenario_results,
        portfolio_impact=portfolio_impact,
        optimisation_candidate=optimisation_candidate,
        verification_verdicts=verification_verdicts,
        generated_at=datetime.now(timezone.utc),
    )
