"""
Realistic-scale tests for `historical_var`, using the SYNTHETIC (not real)
252-day fat-tailed returns fixture from conftest.py.

This module contains no real market data and makes no claim about any
real instrument, index, or historical period. See conftest.py's module
docstring for the fixture's synthetic generation parameters.
"""

import statistics

import pytest

from optifi_quant import historical_var, parametric_var


def test_synthetic_fixture_is_realistic_scale_and_fat_tailed(synthetic_daily_returns):
    """Sanity-check the SYNTHETIC fixture itself before relying on it."""
    assert len(synthetic_daily_returns) == 252

    # Fat tails: at least one daily move beyond 3 standard deviations is
    # expected from a df=4 Student's t series at this sample size, which
    # would be a rare event under a true Gaussian. This is a property
    # check of the synthetic generator, not a claim about real markets.
    sample_std = statistics.pstdev(synthetic_daily_returns)
    sample_mean = statistics.mean(synthetic_daily_returns)
    extreme_moves = [
        r for r in synthetic_daily_returns if abs(r - sample_mean) > 3 * sample_std
    ]
    assert len(extreme_moves) >= 1


def test_historical_var_vs_parametric_var_diverge_at_high_confidence(
    synthetic_daily_returns,
):
    """
    The expected, demonstrable consequence of fat tails: at high
    confidence (99%), historical_var — which makes no distributional
    assumption — should be meaningfully larger than parametric_var, which
    assumes normality and therefore underestimates extreme-percentile
    risk for a fat-tailed series.

    Uses SYNTHETIC data (conftest.py) — not a claim about any real market.
    """
    sample_std = statistics.pstdev(synthetic_daily_returns)

    historical = historical_var(
        returns=synthetic_daily_returns, confidence_level=0.99
    )
    parametric = parametric_var(
        portfolio_value=1.0,  # unit portfolio value -> result is a return fraction, directly comparable to historical_var's result
        portfolio_std_dev=sample_std,
        confidence_level=0.99,
    )

    assert historical.result > parametric.result

    # "Meaningfully larger," not just marginally: require at least a 10%
    # relative excess. The fixture's fixed seed/df (conftest.py) were
    # chosen specifically because they reproducibly clear this margin.
    relative_excess = (historical.result - parametric.result) / parametric.result
    assert relative_excess > 0.10


@pytest.mark.parametrize("confidence_level", [0.90, 0.95, 0.99])
def test_historical_var_at_multiple_confidence_levels(
    synthetic_daily_returns, confidence_level
):
    """historical_var runs correctly at realistic scale (252 points) across several confidence levels."""
    uap = historical_var(
        returns=synthetic_daily_returns, confidence_level=confidence_level
    )
    assert uap.result >= 0.0


def test_historical_var_increases_monotonically_with_confidence(
    synthetic_daily_returns,
):
    """As confidence increases, the loss threshold being estimated moves further into the tail, so VaR should not decrease."""
    var_90 = historical_var(
        returns=synthetic_daily_returns, confidence_level=0.90
    ).result
    var_95 = historical_var(
        returns=synthetic_daily_returns, confidence_level=0.95
    ).result
    var_99 = historical_var(
        returns=synthetic_daily_returns, confidence_level=0.99
    ).result

    assert var_90 <= var_95 <= var_99
