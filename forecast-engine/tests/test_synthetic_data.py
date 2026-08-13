"""Synthetic data generators — determinism (fixed seed, matches this
project's established quant-engine precedent) and shape correctness."""

from optifi_forecast import (
    realised_volatility_series,
    revenue_growth_direction_labels,
    synthetic_company_revenue_growth,
    synthetic_cpi_yoy_series,
    synthetic_index_returns,
)


def test_cpi_series_is_deterministic_given_fixed_seed():
    a = synthetic_cpi_yoy_series(seed=7)
    b = synthetic_cpi_yoy_series(seed=7)
    assert a == b


def test_cpi_series_differs_across_seeds():
    a = synthetic_cpi_yoy_series(seed=1)
    b = synthetic_cpi_yoy_series(seed=2)
    assert a != b


def test_cpi_series_has_requested_length():
    series = synthetic_cpi_yoy_series(n_months=24)
    assert len(series) == 24


def test_index_returns_deterministic_and_correct_length():
    a = synthetic_index_returns(seed=99, n_days=100)
    b = synthetic_index_returns(seed=99, n_days=100)
    assert a == b
    assert len(a) == 100


def test_realised_volatility_series_drops_partial_trailing_window():
    returns = synthetic_index_returns(n_days=100)
    vol = realised_volatility_series(returns, window_days=21)
    assert len(vol) == 100 // 21
    assert all(v > 0 for v in vol)


def test_revenue_growth_series_deterministic():
    a = synthetic_company_revenue_growth(seed=5)
    b = synthetic_company_revenue_growth(seed=5)
    assert a == b


def test_revenue_growth_direction_labels_length_and_values():
    series = [0.01, 0.03, 0.02, 0.02, 0.05]
    labels = revenue_growth_direction_labels(series)
    assert labels == ["up", "down", "down", "up"]
    assert len(labels) == len(series) - 1
