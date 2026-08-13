"""Part B baselines — correctness against hand-computed expected values,
plus the documented market-implied-unavailable failure."""

import pytest
from optifi_shared import UnsupportedFailure

from optifi_forecast import (
    historical_mean_baseline,
    latest_observation_baseline,
    market_implied_baseline,
    rolling_mean_baseline,
    simple_ar1_baseline,
)


def test_latest_observation_baseline():
    assert latest_observation_baseline([1.0, 2.0, 3.0]) == 3.0


def test_latest_observation_baseline_empty_raises():
    with pytest.raises(ValueError):
        latest_observation_baseline([])


def test_historical_mean_baseline():
    assert historical_mean_baseline([1.0, 2.0, 3.0]) == pytest.approx(2.0)


def test_rolling_mean_baseline_uses_only_the_window():
    history = [100.0, 100.0, 1.0, 2.0, 3.0]
    assert rolling_mean_baseline(history, window=3) == pytest.approx(2.0)


def test_rolling_mean_baseline_window_larger_than_history_uses_all():
    history = [1.0, 2.0, 3.0]
    assert rolling_mean_baseline(history, window=10) == pytest.approx(2.0)


def test_simple_ar1_baseline_fits_a_perfect_linear_relationship():
    # x_t = 1.0 + 0.5 * x_{t-1}, exactly, no noise.
    history = [2.0]
    for _ in range(19):
        history.append(1.0 + 0.5 * history[-1])
    forecast = simple_ar1_baseline(history)
    expected_next = 1.0 + 0.5 * history[-1]
    assert forecast == pytest.approx(expected_next, abs=1e-6)


def test_simple_ar1_baseline_falls_back_for_too_little_history():
    assert simple_ar1_baseline([5.0, 7.0]) == 7.0


def test_market_implied_baseline_raises_unsupported_not_a_fabricated_number():
    """'Never fabricate unavailable financial information' — this
    baseline is explicitly withheld rather than silently approximated."""
    with pytest.raises(UnsupportedFailure):
        market_implied_baseline()
