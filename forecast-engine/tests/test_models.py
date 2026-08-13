"""Part C competing model families — econometric (SES) and ML (linear
features), and confirmation they are genuinely different techniques
(not the same formula relabelled)."""

import pytest
from optifi_shared import InsufficientDataFailure

from optifi_forecast import (
    exponential_smoothing_forecast,
    fit_best_alpha,
    fit_linear_feature_model,
    linear_feature_forecast,
    simple_ar1_baseline,
    synthetic_cpi_yoy_series,
)


# --- econometric (SES) ---


def test_ses_forecast_on_flat_series_returns_the_flat_value():
    history = [5.0] * 10
    assert exponential_smoothing_forecast(history) == pytest.approx(5.0)


def test_fit_best_alpha_returns_a_value_from_the_grid():
    history = synthetic_cpi_yoy_series(n_months=30)
    alpha = fit_best_alpha(history)
    assert 0.0 < alpha < 1.0


def test_ses_single_observation_returns_that_observation():
    assert exponential_smoothing_forecast([3.5]) == 3.5


def test_ses_and_ar1_diverge_on_a_trending_series():
    """Confirms the two families are genuinely distinct techniques, not
    the same formula under two names — they should disagree on a
    strongly trending series."""
    history = [float(i) for i in range(20)]  # pure linear trend
    ses_forecast = exponential_smoothing_forecast(history)
    ar1_forecast = simple_ar1_baseline(history)
    # SES lags a strong trend (it averages past levels); AR(1) on a pure
    # trend extrapolates it forward — these should differ meaningfully.
    assert abs(ses_forecast - ar1_forecast) > 1.0


# --- ML (linear features) ---


def test_linear_feature_model_recovers_a_known_linear_relationship():
    # target = 2 * lag1 - 1 * lag2 + 0 * rolling_mean + 0 * trend + 3, exactly.
    history = [1.0, 2.0]
    for _ in range(15):
        lag1, lag2 = history[-1], history[-2]
        history.append(2 * lag1 - 1 * lag2 + 3.0)
    forecast = linear_feature_forecast(history, window=3)
    lag1, lag2 = history[-1], history[-2]
    expected = 2 * lag1 - 1 * lag2 + 3.0
    assert forecast == pytest.approx(expected, abs=1e-6)


def test_linear_feature_model_raises_on_insufficient_data():
    with pytest.raises(InsufficientDataFailure):
        fit_linear_feature_model([1.0, 2.0, 3.0, 4.0], window=3)
