"""
Tests for minimum_variance_hedge_ratio (HEDGING_SPEC.md, Section 4.1).
"""

import pytest
from optifi_shared import InformationClass

from optifi_quant import minimum_variance_hedge_ratio


def test_normal_case_matches_hand_verified_covariance_fixture():
    """
    Reuses test_covariance.py's own hand-verified example directly:
    A=[1,2,3,4,5] (mean=3, deviations=[-2,-1,0,1,2]),
    B=[2,1,4,3,5] (mean=3, deviations=[-1,-2,1,0,2]).
    cov(A,B) = sum(devA*devB)/(n-1) = (2+2+0+0+4)/4 = 8/4 = 2.0
    var(A) = sum(devA^2)/(n-1) = (4+1+0+1+4)/4 = 10/4 = 2.5
    var(B) = sum(devB^2)/(n-1) = (1+4+1+0+4)/4 = 10/4 = 2.5

    h* = cov(A,B) / var(B) = 2.0 / 2.5 = 0.8
    R^2 = cov(A,B)^2 / (var(A)*var(B)) = 4.0 / 6.25 = 0.64
    """
    uap = minimum_variance_hedge_ratio(
        position_returns=[1, 2, 3, 4, 5],
        hedge_instrument_returns=[2, 1, 4, 3, 5],
    )
    assert uap.result["hedge_ratio"] == pytest.approx(0.8)
    assert uap.result["hedge_effectiveness_r_squared"] == pytest.approx(0.64)
    assert uap.information_class == InformationClass.ESTIMATE


def test_perfectly_correlated_series_gives_r_squared_of_one():
    # hedge_instrument is exactly 2x position -> perfect correlation.
    uap = minimum_variance_hedge_ratio(
        position_returns=[1, 2, 3, 4, 5],
        hedge_instrument_returns=[2, 4, 6, 8, 10],
    )
    assert uap.result["hedge_effectiveness_r_squared"] == pytest.approx(1.0)
    # h* = Cov(S,F)/Var(F); with F=2S, Cov(S,F)=2*Var(S), Var(F)=4*Var(S)
    # -> h* = 2*Var(S) / (4*Var(S)) = 0.5.
    assert uap.result["hedge_ratio"] == pytest.approx(0.5)


def test_poor_hedge_effectiveness_is_surfaced_not_hidden():
    """
    A genuinely weakly-correlated pair must still return a real,
    computed hedge_ratio and a real, low hedge_effectiveness_r_squared —
    not omit the field, not raise, not silently substitute a placeholder.
    """
    uap = minimum_variance_hedge_ratio(
        position_returns=[1, 2, 3, 4, 5],
        hedge_instrument_returns=[3, 1, 4, 1, 5],
    )
    assert "hedge_ratio" in uap.result
    assert "hedge_effectiveness_r_squared" in uap.result
    assert uap.result["hedge_effectiveness_r_squared"] == pytest.approx(0.125)
    # Genuinely poor: well below any plausible "good hedge" threshold.
    assert uap.result["hedge_effectiveness_r_squared"] < 0.3
    # The low value is a real number, not None/omitted/clamped away.
    assert isinstance(uap.result["hedge_effectiveness_r_squared"], float)


def test_zero_variance_hedge_instrument_is_guarded_not_a_divide_by_zero():
    with pytest.raises(ValueError, match="hedge_instrument_returns has zero or near-zero variance"):
        minimum_variance_hedge_ratio(
            position_returns=[1, 2, 3, 4, 5],
            hedge_instrument_returns=[3, 3, 3, 3, 3],
        )


def test_zero_variance_position_is_guarded_not_a_divide_by_zero():
    """
    Companion guard: a constant position series makes R^2 undefined too
    (division by Var(S)=0), so this function checks it independently of
    the hedge_instrument_returns guard above.
    """
    with pytest.raises(ValueError, match="position_returns has zero or near-zero variance"):
        minimum_variance_hedge_ratio(
            position_returns=[3, 3, 3, 3, 3],
            hedge_instrument_returns=[1, 2, 3, 4, 5],
        )


def test_records_covariance_matrix_as_a_dependency():
    uap = minimum_variance_hedge_ratio(
        position_returns=[1, 2, 3, 4, 5],
        hedge_instrument_returns=[2, 1, 4, 3, 5],
    )
    assert len(uap.dependencies) == 1
