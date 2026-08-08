"""
Tests for covariance_matrix, correlation_matrix, portfolio_variance
(QUANT_ENGINE_SPEC.md, Section 5.5/9).
"""

import pytest
from optifi_shared import InformationClass

from optifi_quant import correlation_matrix, covariance_matrix, portfolio_variance
from optifi_quant.covariance import _is_positive_semi_definite


# --- covariance_matrix ---


def _known_two_asset_returns() -> dict[str, list[float]]:
    # Hand-verified below (see test docstrings for the arithmetic).
    return {"A": [1, 2, 3, 4, 5], "B": [2, 1, 4, 3, 5]}


def test_covariance_matrix_correct_result_for_known_example():
    # A: [1,2,3,4,5] mean=3, deviations=[-2,-1,0,1,2]
    # B: [2,1,4,3,5] mean=3, deviations=[-1,-2,1,0,2]
    # cov(A,B) = sum(devA*devB)/(n-1) = (2+2+0+0+4)/4 = 8/4 = 2.0
    # var(A) = sum(devA^2)/(n-1) = (4+1+0+1+4)/4 = 10/4 = 2.5
    # var(B) = sum(devB^2)/(n-1) = (1+4+1+0+4)/4 = 10/4 = 2.5
    uap = covariance_matrix(_known_two_asset_returns())

    assert uap.result["A"]["A"] == pytest.approx(2.5)
    assert uap.result["B"]["B"] == pytest.approx(2.5)
    assert uap.result["A"]["B"] == pytest.approx(2.0)
    assert uap.result["B"]["A"] == pytest.approx(2.0)
    assert uap.information_class == InformationClass.ESTIMATE


def test_covariance_matrix_rejects_fewer_than_two_assets():
    with pytest.raises(ValueError):
        covariance_matrix({"A": [1.0, 2.0, 3.0]})


def test_covariance_matrix_rejects_mismatched_series_lengths():
    with pytest.raises(ValueError):
        covariance_matrix({"A": [1.0, 2.0, 3.0], "B": [1.0, 2.0]})


def test_positive_semi_definite_check_fires_on_deliberately_bad_matrix():
    """
    A genuine sample covariance matrix is always PSD by construction, so
    covariance_matrix() itself can't be fed real return data that
    produces a non-PSD result. This test instead proves the underlying
    check function is real and correctly rejects a matrix it's
    mathematically impossible to reach via covariance_matrix: [[1,2],[2,1]]
    has eigenvalues 3 and -1 (by (1-L)^2 - 4 = 0 -> L = 3, -1), so it is
    NOT positive semi-definite.
    """
    bad_matrix = {"A": {"A": 1.0, "B": 2.0}, "B": {"A": 2.0, "B": 1.0}}
    assert _is_positive_semi_definite(bad_matrix, ["A", "B"]) is False

    # A genuinely PSD matrix (e.g. an actual computed covariance matrix)
    # must pass the same check, so the guard isn't just always-false.
    good_matrix = {"A": {"A": 2.5, "B": 2.0}, "B": {"A": 2.0, "B": 2.5}}
    assert _is_positive_semi_definite(good_matrix, ["A", "B"]) is True


# --- correlation_matrix ---


def test_correlation_matrix_diagonal_is_exactly_one():
    uap = correlation_matrix(_known_two_asset_returns())
    assert uap.result["A"]["A"] == pytest.approx(1.0, abs=1e-9)
    assert uap.result["B"]["B"] == pytest.approx(1.0, abs=1e-9)


def test_correlation_matrix_correct_off_diagonal_for_known_example():
    # corr(A,B) = cov(A,B) / (std_A * std_B) = 2.0 / (sqrt(2.5)*sqrt(2.5)) = 2.0/2.5 = 0.8
    uap = correlation_matrix(_known_two_asset_returns())
    assert uap.result["A"]["B"] == pytest.approx(0.8)
    assert uap.result["B"]["A"] == pytest.approx(0.8)
    assert uap.information_class == InformationClass.ESTIMATE


def test_correlation_matrix_rejects_fewer_than_two_assets():
    with pytest.raises(ValueError):
        correlation_matrix({"A": [1.0, 2.0, 3.0]})


def test_correlation_matrix_rejects_mismatched_series_lengths():
    with pytest.raises(ValueError):
        correlation_matrix({"A": [1.0, 2.0, 3.0], "B": [1.0, 2.0]})


def test_correlation_matrix_rejects_constant_series():
    with pytest.raises(ValueError):
        correlation_matrix({"A": [1.0, 1.0, 1.0, 1.0], "B": [1.0, 2.0, 3.0, 4.0]})


# --- portfolio_variance ---


def test_portfolio_variance_correct_result_for_known_example():
    # weights: A=0.6, B=0.4; covariance: AA=0.04, AB=BA=0.01, BB=0.09
    # variance = wA^2*covAA + 2*wA*wB*covAB + wB^2*covBB
    #          = 0.36*0.04 + 2*0.6*0.4*0.01 + 0.16*0.09
    #          = 0.0144 + 0.0048 + 0.0144 = 0.0336
    weights = {"A": 0.6, "B": 0.4}
    covariance = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.09}}

    uap = portfolio_variance(weights, covariance)

    assert uap.result == pytest.approx(0.0336)
    assert uap.information_class == InformationClass.ESTIMATE


def test_portfolio_variance_rejects_weights_not_summing_to_one():
    weights = {"A": 0.5, "B": 0.6}  # sums to 1.1
    covariance = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.09}}
    with pytest.raises(ValueError):
        portfolio_variance(weights, covariance)


def test_portfolio_variance_accepts_weights_within_tolerance():
    weights = {"A": 0.6000001, "B": 0.3999999}  # sums to 1.0 within tolerance
    covariance = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "B": 0.09}}
    uap = portfolio_variance(weights, covariance)
    assert uap.result == pytest.approx(0.0336, rel=1e-4)


def test_portfolio_variance_rejects_mismatched_asset_sets():
    weights = {"A": 0.6, "B": 0.4}
    covariance = {"A": {"A": 0.04, "C": 0.01}, "C": {"A": 0.01, "C": 0.09}}
    with pytest.raises(ValueError):
        portfolio_variance(weights, covariance)


def test_portfolio_variance_rejects_covariance_row_asset_mismatch():
    weights = {"A": 0.6, "B": 0.4}
    covariance = {"A": {"A": 0.04, "B": 0.01}, "B": {"A": 0.01, "C": 0.09}}
    with pytest.raises(ValueError):
        portfolio_variance(weights, covariance)
