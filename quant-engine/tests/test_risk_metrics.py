"""
Tests for quant-engine's Sharpe ratio and VaR functions
(QUANT_ENGINE_SPEC.md, Sections 5.2/5.3/9).
"""

import pytest
from optifi_shared import InformationClass, MissingInputFailure

from optifi_quant import historical_var, parametric_var, sharpe_ratio


# --- sharpe_ratio ---


def test_sharpe_ratio_correct_result_for_known_input():
    uap = sharpe_ratio(portfolio_return=0.08, risk_free_rate=0.03, portfolio_std_dev=0.12)
    expected = (0.08 - 0.03) / 0.12  # = 0.41666...
    assert uap.result == pytest.approx(expected)
    assert uap.information_class == InformationClass.ESTIMATE


def test_sharpe_ratio_raises_on_zero_std_dev():
    with pytest.raises(ValueError):
        sharpe_ratio(portfolio_return=0.08, risk_free_rate=0.03, portfolio_std_dev=0.0)


def test_sharpe_ratio_raises_on_near_zero_std_dev():
    with pytest.raises(ValueError):
        sharpe_ratio(portfolio_return=0.08, risk_free_rate=0.03, portfolio_std_dev=1e-12)


# --- historical_var ---


def test_historical_var_matches_hand_verified_percentile():
    # Sorted returns, 10 values. confidence_level=0.90 -> 10th percentile.
    # Linear interpolation (numpy 'linear' method): rank = 0.10 * (10-1) = 0.9
    # -> between index 0 (-0.20) and index 1 (-0.10), fraction 0.9:
    #    -0.20 + 0.9 * (-0.10 - (-0.20)) = -0.20 + 0.9*0.10 = -0.11
    # VaR (loss magnitude) = -(-0.11) = 0.11
    returns = [-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    uap = historical_var(returns=returns, confidence_level=0.90)
    assert uap.result == pytest.approx(0.11)
    assert uap.information_class == InformationClass.ESTIMATE


def test_historical_var_matches_hand_verified_percentile_unsorted_input():
    # Same data as above, shuffled, to confirm sorting happens internally.
    returns = [0.30, -0.05, 0.10, -0.20, 0.20, 0.0, -0.10, 0.25, 0.05, 0.15]
    uap = historical_var(returns=returns, confidence_level=0.90)
    assert uap.result == pytest.approx(0.11)


def test_historical_var_is_non_negative_even_when_tail_return_is_a_gain():
    returns = [0.01, 0.02, 0.03, 0.04, 0.05]
    uap = historical_var(returns=returns, confidence_level=0.50)
    assert uap.result >= 0.0
    assert uap.result == pytest.approx(0.0)


def test_historical_var_rejects_empty_returns():
    # Phase E1 hardening: the specific, machine-readable category is now
    # asserted, not just "some ValueError" — MissingInputFailure IS a
    # ValueError, so this remains a strengthening, not a behaviour change.
    with pytest.raises(MissingInputFailure):
        historical_var(returns=[], confidence_level=0.95)


def test_historical_var_rejects_invalid_confidence_level():
    with pytest.raises(ValueError):
        historical_var(returns=[0.01, 0.02], confidence_level=1.5)


# --- parametric_var ---


def test_parametric_var_matches_manual_calculation_with_known_z_score():
    # 95% confidence -> z ~= 1.645 (standard reference-table value).
    portfolio_value = 500_000.0
    portfolio_std_dev = 0.12
    z_95 = 1.645
    expected = z_95 * portfolio_std_dev * portfolio_value

    uap = parametric_var(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=0.95,
    )

    assert uap.result == pytest.approx(expected, rel=1e-3)
    assert uap.information_class == InformationClass.ESTIMATE


def test_parametric_var_is_non_negative():
    uap = parametric_var(portfolio_value=100_000.0, portfolio_std_dev=0.10, confidence_level=0.95)
    assert uap.result >= 0.0


def test_parametric_var_rejects_invalid_confidence_level():
    with pytest.raises(ValueError):
        parametric_var(portfolio_value=100_000.0, portfolio_std_dev=0.10, confidence_level=0.0)
