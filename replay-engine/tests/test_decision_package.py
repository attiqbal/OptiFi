"""
Tests for run_replay / HistoricalDecisionPackage — PHASE E5 Part 2
("Replay Workflow").
"""

import pytest
from optifi_replay import get_period, REPLAY_PERIODS
from optifi_replay.decision_package import DURATION_ASSET_ENTITY, EQUITY_ASSET_ENTITY, run_replay
from optifi_verification import VerdictType


def test_run_replay_succeeds_for_every_period():
    """Not cherry-picked — every one of the seven periods must actually
    run end to end."""
    for period in REPLAY_PERIODS:
        package = run_replay(period)
        assert package.period_id == period.period_id


def test_snapshot_excludes_a_genuine_future_portion():
    package = run_replay(get_period("calm_markets"))
    assert len(package.snapshot.excluded_future) > 0
    assert len(package.snapshot.available_uaps) > 0


def test_forecast_is_computed_not_hardcoded():
    from optifi_forecast import exponential_smoothing_forecast

    period = get_period("calm_markets")
    package = run_replay(period)
    # Independently recompute from the period's own truncated series.
    cpi_series = period.cpi_series()
    truncated = cpi_series[: period.cpi_cutoff_month + 1]
    expected = exponential_smoothing_forecast(truncated)
    assert package.forecast_uap.result == pytest.approx(expected)


def test_forecast_never_uses_data_beyond_the_cutoff():
    """Independent proof: the forecast computed from the snapshot must
    match a forecast computed from the EXPLICITLY truncated series, and
    must NOT match one computed from the full (leaked) series whenever
    the two diverge."""
    from optifi_forecast import exponential_smoothing_forecast

    period = get_period("inflation_shock")  # highest volatility -> most likely to diverge
    package = run_replay(period)
    full_series = period.cpi_series()
    truncated = full_series[: period.cpi_cutoff_month + 1]

    forecast_from_truncated = exponential_smoothing_forecast(truncated)
    forecast_from_full = exponential_smoothing_forecast(full_series)

    assert package.forecast_uap.result == pytest.approx(forecast_from_truncated)
    if forecast_from_truncated != pytest.approx(forecast_from_full):
        assert package.forecast_uap.result != pytest.approx(forecast_from_full)


def test_scenario_results_cover_both_portfolio_assets():
    package = run_replay(get_period("calm_markets"))
    assert set(package.scenario_results.keys()) == {DURATION_ASSET_ENTITY, EQUITY_ASSET_ENTITY}


def test_scenario_results_have_genuine_ranges():
    package = run_replay(get_period("calm_markets"))
    for result in package.scenario_results.values():
        assert result.range_low < result.base_case < result.range_high


def test_portfolio_impact_is_independently_recomputable():
    package = run_replay(get_period("calm_markets"))
    weights = package.snapshot.portfolio
    expected = sum(weights[e] * package.scenario_results[e].base_case for e in weights)
    assert package.portfolio_impact.result["portfolio_base_case"] == pytest.approx(expected)


def test_optimisation_candidate_weights_sum_to_one():
    package = run_replay(get_period("calm_markets"))
    weights = package.optimisation_candidate.result["weights"]
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_verification_verdicts_are_all_present_and_not_reject():
    """Every verdict should at least resolve to PASS or PASS_WITH_CAUTION
    for a well-formed, honestly-dated replay — a REJECT here would mean
    this package itself violated its own no-look-ahead discipline."""
    for period in REPLAY_PERIODS:
        package = run_replay(period)
        for name, verdict in package.verification_verdicts.items():
            assert verdict.verdict_type != VerdictType.REJECT, f"{period.period_id}/{name}: {verdict.reasons}"


def test_decision_package_is_frozen():
    package = run_replay(get_period("calm_markets"))
    with pytest.raises(Exception):
        package.period_id = "tampered"


def test_forecast_record_matches_the_forecast_uap():
    package = run_replay(get_period("calm_markets"))
    assert package.forecast_record.predicted_point == pytest.approx(package.forecast_uap.result)
    assert package.forecast_record.forecast_timestamp == package.as_of
