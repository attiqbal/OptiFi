"""
DecisionScorecard — PHASE E5 brief, Part 3 ("Evaluate Realised Outcomes")
and Part 6 ("Decision Scorecard").

"Do not judge every recommendation solely by realised return. A sensible
decision can lose money. Evaluate risk-adjusted decision quality." —
this module's central discipline: every metric here is computed from
REAL held-out future data (the portion of each `HistoricalPeriod`'s
series beyond its cutoff, never used anywhere in `run_replay`), and the
scorecard's own qualitative judgments (Part 6's questions) are derived
FROM those metrics, not asserted independently — a call that lost money
but stayed within its own predicted range is marked
`recommendation_was_risk_sound_despite_outcome=True`, not penalised for
the loss alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from optifi_simulation.scenario_library import INFLATION_SURPRISE_1PP
from optifi_verification import VerdictType

from .decision_package import (
    DURATION_ASSET_ENTITY,
    EQUITY_ASSET_ENTITY,
    MODIFIED_DURATION,
    HistoricalDecisionPackage,
)
from .historical_periods import HistoricalPeriod

_DAYS_PER_MONTH = 30
# Small, documented threshold: turnover below this is treated as
# "not material" for the "were unnecessary trades avoided" question —
# a few percentage points of drift is not a real reallocation decision.
_MATERIAL_TURNOVER_THRESHOLD = 0.05


def _horizon_months(horizon: str) -> int:
    return int(horizon.split("-")[0])


@dataclass(frozen=True)
class DecisionScorecard:
    period_id: str
    as_of: datetime
    regime_label: str

    # --- Part 3: forecast error ---
    forecast_predicted: float
    forecast_realised: float
    forecast_error: float
    forecast_absolute_error: float

    # --- Part 3: scenario coverage ---
    scenario_coverage: dict[str, bool]
    scenario_coverage_rate: float

    # --- Part 3: portfolio-decision outcome ---
    realised_asset_returns: dict[str, float]
    recommended_weights: dict[str, float]
    no_action_weights: dict[str, float]
    realised_return_recommended: float
    realised_return_no_action: float
    opportunity_cost: float  # positive => no-action would have done better
    turnover: float

    # --- Part 3: risk ---
    equity_leg_max_drawdown: float

    # --- Part 6: decision-quality questions, each backed by the above ---
    scenario_range_contained_outcome: bool
    optimisation_respected_constraints: bool
    no_action_would_have_been_better: bool
    recommendation_was_risk_sound_despite_outcome: bool
    turnover_was_material: bool


def _realised_cpi_change(period: HistoricalPeriod, months_ahead: int) -> float:
    series = period.cpi_series()
    start = period.cpi_cutoff_month
    end = start + months_ahead
    if end >= len(series):
        raise ValueError(
            f"_realised_cpi_change: {period.period_id} series (len={len(series)}) does not "
            f"extend {months_ahead} months past the cutoff ({start}) — cannot evaluate."
        )
    return series[end] - series[start]


def _realised_index_return(period: HistoricalPeriod, days_ahead: int) -> tuple[float, list[float]]:
    levels = period.index_price_levels()
    start_day = period.index_cutoff_day
    end_day = start_day + days_ahead
    if end_day >= len(levels):
        raise ValueError(
            f"_realised_index_return: {period.period_id} series (len={len(levels)}) does not "
            f"extend {days_ahead} days past the cutoff ({start_day}) — cannot evaluate."
        )
    path = levels[start_day : end_day + 1]
    return (path[-1] - path[0]) / path[0], path


def _max_drawdown(path: list[float]) -> float:
    peak = path[0]
    max_dd = 0.0
    for level in path:
        peak = max(peak, level)
        drawdown = (level - peak) / peak
        max_dd = min(max_dd, drawdown)
    return max_dd  # <= 0.0


def derive_risk_soundness(realised_return_recommended: float, scenario_coverage: dict[str, bool]) -> bool:
    """
    Part 3: "A sensible decision can lose money. Evaluate risk-adjusted
    decision quality." A recommendation is judged risk-sound despite a
    losing outcome precisely when the loss still fell within what the
    scenario analysis said was plausible (every target's range contained
    the realised move) — the loss was a known, priced-in possibility,
    not evidence the analysis was wrong. Pulled out as its own pure
    function so this judgment can be tested directly against
    hand-picked cases, not only observed incidentally from whichever
    real replay periods happen to produce a loss.
    """
    recommendation_lost_money = realised_return_recommended < 0
    return recommendation_lost_money and bool(scenario_coverage) and all(scenario_coverage.values())


def evaluate_replay(package: HistoricalDecisionPackage, period: HistoricalPeriod) -> DecisionScorecard:
    # --- forecast error (1-month CPI forecast vs. realised next month) ---
    forecast_horizon_months = _horizon_months(package.forecast_record.horizon)
    realised_cpi_change = _realised_cpi_change(period, forecast_horizon_months)
    cpi_at_cutoff = period.cpi_series()[period.cpi_cutoff_month]
    forecast_realised = cpi_at_cutoff + realised_cpi_change
    forecast_predicted = package.forecast_record.predicted_point
    forecast_error = forecast_predicted - forecast_realised

    # --- realised asset returns over the scenario horizon ---
    scenario_horizon_months = _horizon_months(INFLATION_SURPRISE_1PP.horizon)
    realised_cpi_change_scenario_horizon = _realised_cpi_change(period, scenario_horizon_months)
    realised_duration_return = -MODIFIED_DURATION * (realised_cpi_change_scenario_horizon / 100.0)
    realised_equity_return, equity_path = _realised_index_return(
        period, scenario_horizon_months * _DAYS_PER_MONTH
    )
    realised_asset_returns = {
        DURATION_ASSET_ENTITY: realised_duration_return,
        EQUITY_ASSET_ENTITY: realised_equity_return,
    }

    # --- scenario coverage ---
    scenario_coverage = {
        entity_id: (result.range_low <= realised_asset_returns[entity_id] <= result.range_high)
        for entity_id, result in package.scenario_results.items()
    }
    scenario_coverage_rate = sum(scenario_coverage.values()) / len(scenario_coverage)

    # --- portfolio-decision outcome ---
    recommended_weights = package.optimisation_candidate.result["weights"]
    no_action_weights = package.snapshot.portfolio
    realised_return_recommended = sum(recommended_weights[a] * realised_asset_returns[a] for a in recommended_weights)
    realised_return_no_action = sum(no_action_weights[a] * realised_asset_returns[a] for a in no_action_weights)
    opportunity_cost = realised_return_no_action - realised_return_recommended
    turnover = sum(abs(recommended_weights[a] - no_action_weights.get(a, 0.0)) for a in recommended_weights) / 2

    equity_leg_max_drawdown = _max_drawdown(equity_path)

    # --- Part 6 questions, each derived from the above, not asserted independently ---
    optimisation_respected_constraints = package.verification_verdicts["loss_cap"].verdict_type != VerdictType.REJECT
    recommendation_was_risk_sound_despite_outcome = derive_risk_soundness(
        realised_return_recommended, scenario_coverage
    )

    return DecisionScorecard(
        period_id=period.period_id,
        as_of=package.as_of,
        regime_label=period.regime_label,
        forecast_predicted=forecast_predicted,
        forecast_realised=forecast_realised,
        forecast_error=forecast_error,
        forecast_absolute_error=abs(forecast_error),
        scenario_coverage=scenario_coverage,
        scenario_coverage_rate=scenario_coverage_rate,
        realised_asset_returns=realised_asset_returns,
        recommended_weights=recommended_weights,
        no_action_weights=no_action_weights,
        realised_return_recommended=realised_return_recommended,
        realised_return_no_action=realised_return_no_action,
        opportunity_cost=opportunity_cost,
        turnover=turnover,
        equity_leg_max_drawdown=equity_leg_max_drawdown,
        scenario_range_contained_outcome=(scenario_coverage_rate == 1.0),
        optimisation_respected_constraints=optimisation_respected_constraints,
        no_action_would_have_been_better=(opportunity_cost > 0),
        recommendation_was_risk_sound_despite_outcome=recommendation_was_risk_sound_despite_outcome,
        turnover_was_material=(turnover >= _MATERIAL_TURNOVER_THRESHOLD),
    )
