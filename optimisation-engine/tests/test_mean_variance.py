"""
Tests for minimize_variance (OPTIMISATION_ENGINE_SPEC.md, Section 5.1).
"""

import numpy as np
import pytest
from optifi_shared import InformationClass

from optifi_optimisation import minimize_variance

ASSET_ORDER = ["A", "B", "C"]
EXPECTED_RETURNS = {"A": 0.05, "B": 0.08, "C": 0.12}
# Deliberately uncorrelated (diagonal-only) covariance, so an independent
# closed-form Lagrangian solve (below) is tractable as a cross-check
# against cvxpy's result.
COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0, "C": 0.0},
    "B": {"A": 0.0, "B": 0.09, "C": 0.0},
    "C": {"A": 0.0, "B": 0.0, "C": 0.16},
}


def _closed_form_min_variance(mu: np.ndarray, sigma: np.ndarray, target_return: float) -> np.ndarray:
    """
    Independent cross-check, NOT using cvxpy: solves the same
    minimum-variance problem (sum(w)=1, w.mu=target_return, no inequality
    bounds) via its KKT/Lagrangian first-order conditions directly as a
    linear system:

        2*Sigma*w - lambda1*1 - lambda2*mu = 0
        1^T w = 1
        mu^T w = target_return

    This is the standard closed-form two-fund solution for an
    equality-constrained mean-variance problem, used here only to verify
    minimize_variance's cvxpy-based result independently.
    """
    n = len(mu)
    a = np.zeros((n + 2, n + 2))
    a[:n, :n] = 2 * sigma
    a[:n, n] = -1.0
    a[:n, n + 1] = -mu
    a[n, :n] = 1.0
    a[n + 1, :n] = mu

    b = np.zeros(n + 2)
    b[n] = 1.0
    b[n + 1] = target_return

    solution = np.linalg.solve(a, b)
    return solution[:n]


def test_minimize_variance_matches_independent_closed_form_solution():
    target_return = 0.09
    mu = np.array([EXPECTED_RETURNS[a] for a in ASSET_ORDER])
    sigma = np.array([[COVARIANCE[a][b] for b in ASSET_ORDER] for a in ASSET_ORDER])
    expected_weights = _closed_form_min_variance(mu, sigma, target_return)
    expected_variance = float(expected_weights @ sigma @ expected_weights)

    uap = minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=target_return)

    for i, asset in enumerate(ASSET_ORDER):
        assert uap.result["weights"][asset] == pytest.approx(expected_weights[i], abs=1e-5)
    assert uap.result["portfolio_variance"] == pytest.approx(expected_variance, abs=1e-6)
    assert uap.information_class == InformationClass.ESTIMATE


def test_minimize_variance_weights_sum_to_one():
    uap = minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=0.09)
    total = sum(uap.result["weights"].values())
    assert total == pytest.approx(1.0, abs=1e-6)


def test_minimize_variance_respects_bounds_when_they_bind():
    # The unconstrained (default-bounds) solution puts ~0.413 in C (see
    # the closed-form test above). max_weight=0.405 sits just below that,
    # forcing C to bind exactly at the bound while still leaving enough
    # feasible room (max achievable return at this bound is ~0.0905,
    # just above the 0.09 target) for the solver to redistribute A/B —
    # verified empirically before choosing this value, not asserted blind.
    max_weight = 0.405
    uap = minimize_variance(
        EXPECTED_RETURNS,
        COVARIANCE,
        target_return=0.09,
        min_weight=0.0,
        max_weight=max_weight,
    )
    for weight in uap.result["weights"].values():
        assert -1e-6 <= weight <= max_weight + 1e-6
    assert uap.result["weights"]["C"] == pytest.approx(max_weight, abs=1e-4)
    total = sum(uap.result["weights"].values())
    assert total == pytest.approx(1.0, abs=1e-6)


def test_minimize_variance_raises_on_mismatched_asset_sets():
    mismatched_returns = {"A": 0.05, "B": 0.08, "D": 0.12}
    with pytest.raises(ValueError):
        minimize_variance(mismatched_returns, COVARIANCE, target_return=0.09)


def test_minimize_variance_raises_clear_error_on_infeasible_target_return():
    # Achievable expected return under default bounds [0,1] is
    # [min(mu), max(mu)] = [0.05, 0.12]. 0.20 is well outside that range,
    # so no feasible portfolio exists.
    with pytest.raises(ValueError, match="no feasible portfolio"):
        minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=0.20)


def test_minimize_variance_information_class_is_estimate():
    uap = minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=0.09)
    assert uap.information_class == InformationClass.ESTIMATE
