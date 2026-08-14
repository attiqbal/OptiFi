"""
Tests for the historical replay dataset — PHASE E5 Part 4: "a manageable
set of historically meaningful periods representing multiple regimes...
Do not cherry-pick only successful periods."
"""

from optifi_replay import get_period, REPLAY_PERIODS


def test_seven_periods_matching_the_briefs_own_list():
    expected_ids = {
        "calm_markets",
        "tightening",
        "easing",
        "inflation_shock",
        "equity_stress",
        "recession_fear",
        "fx_commodity_volatility",
    }
    assert {p.period_id for p in REPLAY_PERIODS} == expected_ids
    assert len(REPLAY_PERIODS) == 7


def test_periods_are_not_all_positive_not_cherry_picked():
    """At least one period must have negative expected equity drift —
    proof this isn't a dataset stacked only with success stories."""
    means = [p.index_annual_mean for p in REPLAY_PERIODS]
    assert any(m < 0 for m in means)
    assert any(m > 0 for m in means)


def test_periods_span_a_real_range_of_volatility():
    vols = [p.index_annual_vol for p in REPLAY_PERIODS]
    assert max(vols) / min(vols) > 2.0  # genuinely different, not cosmetic variation


def test_periods_span_a_real_range_of_inflation_levels():
    levels = [p.cpi_level for p in REPLAY_PERIODS]
    assert max(levels) - min(levels) > 3.0


def test_each_period_produces_a_genuinely_different_series():
    series_by_period = {p.period_id: tuple(p.cpi_series()) for p in REPLAY_PERIODS}
    # every period's series is distinct from every other's
    assert len(set(series_by_period.values())) == len(REPLAY_PERIODS)


def test_get_period_returns_the_matching_definition():
    period = get_period("inflation_shock")
    assert period.regime_label == "high-inflation"


def test_get_period_unknown_id_raises():
    import pytest

    with pytest.raises(KeyError):
        get_period("not_a_real_period")


def test_cutoff_is_strictly_within_series_bounds_for_every_period():
    for p in REPLAY_PERIODS:
        assert 0 < p.cpi_cutoff_month < p.cpi_n_months
        assert 0 < p.index_cutoff_day < p.index_n_days


def test_series_generation_is_deterministic():
    period = get_period("calm_markets")
    assert period.cpi_series() == period.cpi_series()
    assert period.index_returns() == period.index_returns()
