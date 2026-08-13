"""
Tests for the Phase E1 hardening at optimisation-engine's boundary:
`covariance` is accepted as a raw dict, so the optimiser must not
blindly assume it is symmetric/positive-semi-definite merely because
quant-engine's covariance_matrix normally guarantees that. These tests
prove the independent boundary check actually fires — required test
category #6, "optimiser receiving invalid covariance."
"""

import pytest

from optifi_optimisation import minimize_variance, minimize_variance_with_loss_cap

EXPECTED_RETURNS = {"A": 0.05, "B": 0.08, "C": 0.12}
VALID_COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0, "C": 0.0},
    "B": {"A": 0.0, "B": 0.09, "C": 0.0},
    "C": {"A": 0.0, "B": 0.0, "C": 0.16},
}
TARGET_RETURN = 0.09


def test_valid_covariance_passes_the_boundary_check():
    """Control case: confirms the new guard doesn't reject legitimate input."""
    result = minimize_variance(EXPECTED_RETURNS, VALID_COVARIANCE, TARGET_RETURN)
    assert abs(sum(result.result["weights"].values()) - 1.0) < 1e-6


def test_asymmetric_covariance_is_rejected():
    """
    A hand-constructed covariance matrix where Cov(A,B) != Cov(B,A) is
    not a valid covariance matrix at all -- must be caught explicitly,
    not silently passed to the eigenvalue check (which only reads one
    triangle and cannot detect asymmetry by itself).
    """
    asymmetric_covariance = {
        "A": {"A": 0.04, "B": 0.02, "C": 0.0},
        "B": {"A": 0.05, "B": 0.09, "C": 0.0},  # 0.05 != 0.02 above
        "C": {"A": 0.0, "B": 0.0, "C": 0.16},
    }
    with pytest.raises(ValueError, match="not symmetric"):
        minimize_variance(EXPECTED_RETURNS, asymmetric_covariance, TARGET_RETURN)


def test_non_positive_semi_definite_covariance_is_rejected():
    """
    A symmetric but non-PSD matrix (negative eigenvalue) does not
    represent a mathematically valid covariance structure -- convexity
    the solver relies on (assume_PSD=True) would not actually hold.
    Hand-constructed to have off-diagonal covariance larger than the
    Cauchy-Schwarz bound allows (Cov(A,B)^2 > Var(A)*Var(B)), which
    guarantees a negative eigenvalue.
    """
    non_psd_covariance = {
        "A": {"A": 0.01, "B": 0.5, "C": 0.0},
        "B": {"A": 0.5, "B": 0.01, "C": 0.0},  # symmetric, but |0.5| >> sqrt(0.01*0.01)=0.01
        "C": {"A": 0.0, "B": 0.0, "C": 0.16},
    }
    with pytest.raises(ValueError, match="not positive semi-definite"):
        minimize_variance(EXPECTED_RETURNS, non_psd_covariance, TARGET_RETURN)


def test_asymmetric_covariance_rejected_for_loss_cap_variant_too():
    """The boundary check is shared (_validate_and_build_matrices) --
    confirms minimize_variance_with_loss_cap gets the same protection,
    not just the base function."""
    asymmetric_covariance = {
        "A": {"A": 0.04, "B": 0.02, "C": 0.0},
        "B": {"A": 0.05, "B": 0.09, "C": 0.0},
        "C": {"A": 0.0, "B": 0.0, "C": 0.16},
    }
    with pytest.raises(ValueError, match="not symmetric"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS,
            asymmetric_covariance,
            TARGET_RETURN,
            portfolio_value=1_000_000.0,
            max_single_period_loss=1_000_000.0,
            confidence_level=0.95,
        )


def test_non_positive_semi_definite_covariance_rejected_for_loss_cap_variant_too():
    non_psd_covariance = {
        "A": {"A": 0.01, "B": 0.5, "C": 0.0},
        "B": {"A": 0.5, "B": 0.01, "C": 0.0},
        "C": {"A": 0.0, "B": 0.0, "C": 0.16},
    }
    with pytest.raises(ValueError, match="not positive semi-definite"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS,
            non_psd_covariance,
            TARGET_RETURN,
            portfolio_value=1_000_000.0,
            max_single_period_loss=1_000_000.0,
            confidence_level=0.95,
        )
