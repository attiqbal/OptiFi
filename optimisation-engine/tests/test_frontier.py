"""
Tests for the efficient frontier (OPTIMISATION_ENGINE_SPEC.md Section
5.3) and the maximum Sharpe ratio / tangency portfolio (Section 5.2).

optifi_verification and optifi_quant are [dev]-only test dependencies of
this package (see pyproject.toml) -- used here to independently
re-verify frontier points respect the loss cap, and to prove the real
end-to-end wiring into quant-engine's investment_efficiency. Production
code in optifi_optimisation does not import optifi_verification.
"""

import pytest
from optifi_quant import investment_efficiency
from optifi_verification import VerdictType, verify_loss_cap_candidate

from optifi_optimisation import efficient_frontier, maximum_sharpe_ratio
from optifi_optimisation.frontier import _FRONTIER_SWEEP_POINT_COUNT, _global_minimum_variance_return
from optifi_optimisation.mean_variance import _validate_and_build_matrices

EXPECTED_RETURNS = {"A": 0.05, "B": 0.08, "C": 0.12}
COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0, "C": 0.0},
    "B": {"A": 0.0, "B": 0.09, "C": 0.0},
    "C": {"A": 0.0, "B": 0.0, "C": 0.16},
}
PORTFOLIO_VALUE = 1_000_000.0
CONFIDENCE_LEVEL = 0.95

# Two uncorrelated assets, used for maximum_sharpe_ratio's hand-checkable
# case below -- see that test's docstring for the closed-form derivation.
TWO_ASSET_RETURNS = {"A": 0.05, "B": 0.10}
TWO_ASSET_COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0},
    "B": {"A": 0.0, "B": 0.09},
}
RISK_FREE_RATE = 0.02


# --- efficient_frontier ---


def test_sweep_bounds_are_computed_not_hardcoded():
    """
    The lower bound must equal the global minimum-variance portfolio's
    own achieved return (computed independently here, the same way
    _global_minimum_variance_return does it internally); the upper bound
    must equal the single highest expected return among the provided
    assets (0.12, asset C).
    """
    asset_order, n, mu, sigma = _validate_and_build_matrices(EXPECTED_RETURNS, COVARIANCE, "test")
    expected_lower_bound = _global_minimum_variance_return(mu, sigma, n, 0.0, 1.0, "test")

    uap = efficient_frontier(
        EXPECTED_RETURNS,
        COVARIANCE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    frontier_range = uap.result["target_return_range"]
    assert frontier_range["min"] == pytest.approx(expected_lower_bound)
    assert frontier_range["max"] == pytest.approx(0.12)  # max(EXPECTED_RETURNS.values())


def test_sweep_bounds_change_with_different_inputs():
    """
    Confirms the bounds are genuinely COMPUTED from the inputs, not
    coincidentally hardcoded to match this test file's usual fixture --
    a different expected_returns/covariance produces different bounds.
    """
    different_returns = {"X": 0.03, "Y": 0.20}
    different_covariance = {"X": {"X": 0.01, "Y": 0.0}, "Y": {"X": 0.0, "Y": 0.05}}

    uap = efficient_frontier(
        different_returns,
        different_covariance,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    frontier_range = uap.result["target_return_range"]
    assert frontier_range["max"] == pytest.approx(0.20)
    # Global min-variance return for two uncorrelated assets is a
    # variance-weighted average strictly between the two individual
    # returns, not equal to either fixture's own bounds above.
    assert 0.03 < frontier_range["min"] < 0.20


def test_infeasible_points_are_skipped_and_recorded_not_silently_dropped():
    """
    A cap tight enough to reject the higher-risk, higher-return end of
    the sweep, but loose enough to accept the lower-risk end, produces a
    MIX of feasible and skipped points -- and every skip must be
    recorded, by its exact target_return and reason, in `limitations`.
    """
    uap = efficient_frontier(
        EXPECTED_RETURNS,
        COVARIANCE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=350_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    result = uap.result
    assert result["skipped_point_count"] > 0
    assert result["feasible_point_count"] > 0
    assert result["feasible_point_count"] + result["skipped_point_count"] == _FRONTIER_SWEEP_POINT_COUNT
    assert len(result["frontier_points"]) == result["feasible_point_count"]

    skip_limitation = next(lim for lim in uap.limitations if "skipped" in lim)
    assert str(result["skipped_point_count"]) in skip_limitation
    # At least one specific skipped target_return and its reason must be
    # named, not just a bare count.
    assert "target_return=" in skip_limitation
    assert "loss cap" in skip_limitation


def test_no_points_skipped_when_cap_is_generous():
    uap = efficient_frontier(
        EXPECTED_RETURNS,
        COVARIANCE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    result = uap.result
    assert result["skipped_point_count"] == 0
    assert result["feasible_point_count"] == _FRONTIER_SWEEP_POINT_COUNT
    skip_limitation = next(lim for lim in uap.limitations if "skipped" in lim)
    assert "none" in skip_limitation


def test_raises_when_every_swept_point_is_infeasible():
    with pytest.raises(ValueError, match="every swept target_return was infeasible"):
        efficient_frontier(
            EXPECTED_RETURNS,
            COVARIANCE,
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=1_000.0,  # far too tight for this asset set
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_every_frontier_point_independently_respects_the_loss_cap():
    """
    Independently re-verify EVERY returned frontier point via
    verification-engine's verify_loss_cap_candidate -- not trusting
    optimisation-engine's own self-report, consistent with
    VERIFICATION_FRAMEWORK.md Section 5.5's independent-re-check
    principle.
    """
    cap = 500_000.0
    uap = efficient_frontier(
        EXPECTED_RETURNS,
        COVARIANCE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=cap,
        confidence_level=CONFIDENCE_LEVEL,
    )
    points = uap.result["frontier_points"]
    assert len(points) > 0

    for point in points:
        verdict = verify_loss_cap_candidate(
            weights=point["weights"],
            expected_returns=EXPECTED_RETURNS,
            covariance=COVARIANCE,
            target_return=point["target_return"],
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=cap,
            confidence_level=CONFIDENCE_LEVEL,
            min_weight=0.0,
            max_weight=1.0,
        )
        assert verdict.verdict_type == VerdictType.PASS, (
            f"frontier point at target_return={point['target_return']!r} "
            f"failed independent verification: {verdict.reasons}"
        )


def test_frontier_information_class_is_estimate():
    uap = efficient_frontier(
        EXPECTED_RETURNS,
        COVARIANCE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    from optifi_shared import InformationClass

    assert uap.information_class == InformationClass.ESTIMATE


def test_frontier_docstring_and_uap_mark_loss_cap_as_designed():
    uap = efficient_frontier(
        EXPECTED_RETURNS,
        COVARIANCE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert "DESIGNED" in efficient_frontier.__doc__
    assert "DESIGNED" in uap.producer
    assert any("DESIGNED" in a for a in uap.assumptions)


# --- maximum_sharpe_ratio ---


def test_max_sharpe_matches_closed_form_uncorrelated_case():
    """
    For UNCORRELATED assets, the unconstrained tangency portfolio has a
    known closed-form solution: w_i is proportional to
    (mu_i - R_f) / sigma_i^2 (the standard result from w ~ Sigma^-1 (mu
    - R_f*1) when Sigma is diagonal). Hand-verified here:

        A: (0.05 - 0.02) / 0.04 = 0.75
        B: (0.10 - 0.02) / 0.09 = 0.888888...
        sum = 1.638888...
        w_A = 0.75 / 1.638888... = 0.457627118644...
        w_B = 0.888888.../1.638888... = 0.542372881356...

    A generous loss cap (far above what this portfolio's own VaR could
    be) keeps the loss-cap constraint from binding, isolating the
    reformulation's correctness on the unconstrained tangency point.
    """
    uap = maximum_sharpe_ratio(
        TWO_ASSET_RETURNS,
        TWO_ASSET_COVARIANCE,
        risk_free_rate=RISK_FREE_RATE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=10_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    weights = uap.result["weights"]
    assert weights["A"] == pytest.approx(0.75 / 1.638888888888889, abs=1e-6)
    assert weights["B"] == pytest.approx(0.8888888888888888 / 1.638888888888889, abs=1e-6)

    expected_return = weights["A"] * 0.05 + weights["B"] * 0.10
    expected_variance = weights["A"] ** 2 * 0.04 + weights["B"] ** 2 * 0.09
    expected_sharpe = (expected_return - RISK_FREE_RATE) / (expected_variance**0.5)
    assert uap.result["sharpe_ratio"] == pytest.approx(expected_sharpe, abs=1e-6)


def test_max_sharpe_weights_sum_to_one():
    uap = maximum_sharpe_ratio(
        EXPECTED_RETURNS,
        COVARIANCE,
        risk_free_rate=0.02,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert sum(uap.result["weights"].values()) == pytest.approx(1.0, abs=1e-6)


def test_max_sharpe_respects_a_generous_loss_cap():
    cap = 1_000_000.0
    uap = maximum_sharpe_ratio(
        EXPECTED_RETURNS,
        COVARIANCE,
        risk_free_rate=0.02,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=cap,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert uap.result["value_at_risk"] <= cap


def test_max_sharpe_loss_cap_actually_binds_when_tight():
    """
    The core requirement: a cap tighter than the unconstrained tangency
    portfolio's own VaR (~307,073, from the two-asset closed-form case)
    but looser than the global minimum-variance portfolio's VaR
    (~273,720) must produce a DIFFERENT, lower-risk portfolio than the
    unconstrained case -- proving the SOC reformulation of the loss cap
    genuinely constrains the solution, not merely computed and ignored.
    """
    unconstrained = maximum_sharpe_ratio(
        TWO_ASSET_RETURNS,
        TWO_ASSET_COVARIANCE,
        risk_free_rate=RISK_FREE_RATE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=10_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    tight_cap = 290_000.0
    constrained = maximum_sharpe_ratio(
        TWO_ASSET_RETURNS,
        TWO_ASSET_COVARIANCE,
        risk_free_rate=RISK_FREE_RATE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=tight_cap,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert constrained.result["value_at_risk"] <= tight_cap + 1e-3
    assert abs(constrained.result["weights"]["A"] - unconstrained.result["weights"]["A"]) > 1e-4
    # The cap genuinely binds -- the constrained solution's VaR sits at
    # (approximately) the cap boundary, not comfortably below it.
    assert constrained.result["value_at_risk"] == pytest.approx(tight_cap, abs=1.0)


def test_max_sharpe_raises_when_infeasible():
    with pytest.raises(ValueError, match="infeasible"):
        maximum_sharpe_ratio(
            TWO_ASSET_RETURNS,
            TWO_ASSET_COVARIANCE,
            risk_free_rate=RISK_FREE_RATE,
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=1_000.0,  # far too tight
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_max_sharpe_candidate_independently_verified_by_verification_engine():
    uap = maximum_sharpe_ratio(
        EXPECTED_RETURNS,
        COVARIANCE,
        risk_free_rate=0.02,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    achieved_return = sum(w * EXPECTED_RETURNS[a] for a, w in uap.result["weights"].items())

    verdict = verify_loss_cap_candidate(
        weights=uap.result["weights"],
        expected_returns=EXPECTED_RETURNS,
        covariance=COVARIANCE,
        target_return=achieved_return,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    assert verdict.verdict_type == VerdictType.PASS


def test_max_sharpe_docstring_and_uap_mark_loss_cap_as_designed():
    uap = maximum_sharpe_ratio(
        EXPECTED_RETURNS,
        COVARIANCE,
        risk_free_rate=0.02,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert "DESIGNED" in maximum_sharpe_ratio.__doc__
    assert "DESIGNED" in uap.producer


# --- End-to-end wiring: maximum_sharpe_ratio -> investment_efficiency ---


def test_investment_efficiency_consumes_a_real_maximum_sharpe_ratio_output():
    """
    A genuine end-to-end wiring test, not two isolated unit tests:
    maximum_sharpe_ratio's REAL output UAP is fed into
    investment_efficiency, and the numbers are cross-checked against
    each other, not against hand-picked fixture values.

    investment_efficiency's max_achievable_sharpe_ratio parameter
    expects a UAP whose .result IS the scalar Sharpe ratio;
    maximum_sharpe_ratio's own UAP.result is a richer dict (weights,
    VaR, portfolio_return alongside the ratio) matching
    minimize_variance_with_loss_cap's own dict-result convention. The
    adapter step below (model_copy, swapping only .result) is the
    legitimate integration-point translation between the two engines'
    UAP shapes -- it preserves the original id/provenance, it does not
    fabricate a new upstream packet.
    """
    max_sharpe_uap = maximum_sharpe_ratio(
        EXPECTED_RETURNS,
        COVARIANCE,
        risk_free_rate=0.02,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    scalar_max_sharpe_uap = max_sharpe_uap.model_copy(
        update={"result": max_sharpe_uap.result["sharpe_ratio"]}
    )
    # The adapter must preserve the ORIGINAL optimisation-engine UAP's
    # id -- investment_efficiency's dependency recording relies on it.
    assert scalar_max_sharpe_uap.id == max_sharpe_uap.id

    # A portfolio that achieves exactly HALF the max-achievable Sharpe
    # ratio at some (different) risk level -- deliberately not equal to
    # the tangency portfolio itself, to prove the ratio is real, not a
    # trivial 100% match by construction.
    half_sharpe_return = 0.02 + 0.5 * max_sharpe_uap.result["sharpe_ratio"] * 0.10

    ie_uap = investment_efficiency(
        portfolio_return=half_sharpe_return,
        risk_free_rate=0.02,
        portfolio_std_dev=0.10,
        max_achievable_sharpe_ratio=scalar_max_sharpe_uap,
    )

    assert ie_uap.result == pytest.approx(50.0, abs=1e-6)
    assert max_sharpe_uap.id in ie_uap.dependencies


def test_investment_efficiency_scores_100_when_portfolio_is_the_tangency_portfolio_itself():
    """
    If the "achieved" portfolio literally IS optimisation-engine's own
    tangency portfolio (the real maximum achievable), Investment
    efficiency must score exactly 100 -- the cleanest possible
    end-to-end sanity check that the two engines' numbers genuinely
    agree with each other, not just structurally compatible.
    """
    max_sharpe_uap = maximum_sharpe_ratio(
        TWO_ASSET_RETURNS,
        TWO_ASSET_COVARIANCE,
        risk_free_rate=RISK_FREE_RATE,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=10_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    scalar_max_sharpe_uap = max_sharpe_uap.model_copy(
        update={"result": max_sharpe_uap.result["sharpe_ratio"]}
    )

    weights = max_sharpe_uap.result["weights"]
    achieved_return = sum(w * TWO_ASSET_RETURNS[a] for a, w in weights.items())
    achieved_variance = sum(
        weights[a] * weights[b] * TWO_ASSET_COVARIANCE[a][b]
        for a in weights
        for b in weights
    )

    ie_uap = investment_efficiency(
        portfolio_return=achieved_return,
        risk_free_rate=RISK_FREE_RATE,
        portfolio_std_dev=achieved_variance**0.5,
        max_achievable_sharpe_ratio=scalar_max_sharpe_uap,
    )
    assert ie_uap.result == pytest.approx(100.0, abs=1e-4)
