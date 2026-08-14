"""
Tests for DecisionScorecard / evaluate_replay — PHASE E5 Part 3
("Evaluate Realised Outcomes") and Part 6 ("Decision Scorecard").
"""

import pytest
from optifi_replay import derive_risk_soundness, evaluate_replay, get_period, REPLAY_PERIODS, run_replay


def test_evaluate_replay_succeeds_for_every_period():
    for period in REPLAY_PERIODS:
        package = run_replay(period)
        scorecard = evaluate_replay(package, period)
        assert scorecard.period_id == period.period_id


def test_forecast_error_is_independently_recomputable():
    period = get_period("calm_markets")
    package = run_replay(period)
    scorecard = evaluate_replay(package, period)

    full_series = period.cpi_series()
    realised = full_series[period.cpi_cutoff_month + 1]
    expected_error = package.forecast_record.predicted_point - realised
    assert scorecard.forecast_error == pytest.approx(expected_error)
    assert scorecard.forecast_realised == pytest.approx(realised)


def test_scenario_coverage_boolean_matches_the_actual_range_check():
    period = get_period("calm_markets")
    package = run_replay(period)
    scorecard = evaluate_replay(package, period)

    for entity_id, covered in scorecard.scenario_coverage.items():
        result = package.scenario_results[entity_id]
        realised = scorecard.realised_asset_returns[entity_id]
        assert covered == (result.range_low <= realised <= result.range_high)


def test_scenario_range_contained_outcome_matches_coverage_rate():
    for period in REPLAY_PERIODS:
        package = run_replay(period)
        scorecard = evaluate_replay(package, period)
        assert scorecard.scenario_range_contained_outcome == (scorecard.scenario_coverage_rate == 1.0)


def test_opportunity_cost_is_independently_recomputable():
    period = get_period("tightening")
    package = run_replay(period)
    scorecard = evaluate_replay(package, period)

    expected = scorecard.realised_return_no_action - scorecard.realised_return_recommended
    assert scorecard.opportunity_cost == pytest.approx(expected)


def test_no_action_would_have_been_better_matches_opportunity_cost_sign():
    for period in REPLAY_PERIODS:
        package = run_replay(period)
        scorecard = evaluate_replay(package, period)
        assert scorecard.no_action_would_have_been_better == (scorecard.opportunity_cost > 0)


def test_turnover_is_independently_recomputable():
    period = get_period("calm_markets")
    package = run_replay(period)
    scorecard = evaluate_replay(package, period)

    expected = (
        sum(
            abs(scorecard.recommended_weights[a] - scorecard.no_action_weights.get(a, 0.0))
            for a in scorecard.recommended_weights
        )
        / 2
    )
    assert scorecard.turnover == pytest.approx(expected)


def test_max_drawdown_is_never_positive():
    for period in REPLAY_PERIODS:
        package = run_replay(period)
        scorecard = evaluate_replay(package, period)
        assert scorecard.equity_leg_max_drawdown <= 0.0


def test_optimisation_respected_constraints_reflects_the_real_verdict():
    from optifi_verification import VerdictType

    period = get_period("calm_markets")
    package = run_replay(period)
    scorecard = evaluate_replay(package, period)
    assert scorecard.optimisation_respected_constraints == (
        package.verification_verdicts["loss_cap"].verdict_type != VerdictType.REJECT
    )


# --- Part 3: "a sensible decision can lose money" — tested directly, not just observed ---


def test_risk_soundness_true_when_loss_occurred_but_every_range_covered_it():
    assert derive_risk_soundness(-0.05, {"asset-a": True, "asset-b": True}) is True


def test_risk_soundness_false_when_loss_occurred_and_a_range_missed_it():
    assert derive_risk_soundness(-0.05, {"asset-a": True, "asset-b": False}) is False


def test_risk_soundness_false_when_no_loss_occurred_even_if_ranges_missed():
    """A gain outside the predicted range isn't 'unsound' in the sense
    this question asks about — it's specifically about losses."""
    assert derive_risk_soundness(0.05, {"asset-a": False}) is False


def test_risk_soundness_false_with_no_coverage_data_at_all():
    assert derive_risk_soundness(-0.05, {}) is False


def test_risk_soundness_true_requires_ALL_targets_covered_not_just_some():
    assert derive_risk_soundness(-0.05, {"a": True, "b": True, "c": False}) is False


# --- Part 4: honest, not cherry-picked — the scorecard must be able to report BAD outcomes ---


def test_scorecards_across_the_seven_periods_are_not_uniformly_flattering():
    """If every period scored perfectly on every question, that would
    itself be suspicious — proof this scorecard can and does surface
    real shortcomings, not just favourable results."""
    scorecards = [evaluate_replay(run_replay(p), p) for p in REPLAY_PERIODS]
    coverage_rates = [s.scenario_coverage_rate for s in scorecards]
    assert not all(rate == 1.0 for rate in coverage_rates), (
        "every period achieved perfect scenario coverage — suspiciously flattering; "
        "expected genuine variation, including real misses, across seven independently "
        "drawn regimes"
    )
