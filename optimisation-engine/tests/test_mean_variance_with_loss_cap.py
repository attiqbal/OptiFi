"""
Tests for minimize_variance_with_loss_cap — Gap 1 fix (this function was
specified but never implemented). Solves the same Section 5.1 problem as
minimize_variance, plus the mandate's single-period loss cap enforced as
a solver constraint.

A note on "binding": for a FIXED target_return, minimize_variance already
finds the global minimum-variance portfolio — nothing can have lower
variance at that same target_return. Layering "variance <= cap" on top of
that same objective therefore has exactly two possible effects, never a
third: the constraint is either slack (cap >= the achievable minimum,
result identical to minimize_variance's own answer) or the whole problem
is infeasible (cap < the achievable minimum) — it can never produce a
*different*, still-feasible result, because nothing feasible could beat
the unconstrained minimum in the first place. "Binding, demonstrably
changing the result" is therefore tested here as: the same target_return
that minimize_variance happily accepts, minimize_variance_with_loss_cap
correctly REFUSES once the cap is tighter than that candidate's real VaR
— a genuine, solver-enforced difference in outcome (accept vs. reject),
not a cosmetic weight change. See test_loss_cap_below_achievable_var_
rejects_a_candidate_minimize_variance_would_have_accepted below.
"""

import pytest
from optifi_quant import parametric_var

from optifi_optimisation import minimize_variance, minimize_variance_with_loss_cap

ASSET_ORDER = ["A", "B", "C"]
EXPECTED_RETURNS = {"A": 0.05, "B": 0.08, "C": 0.12}
COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0, "C": 0.0},
    "B": {"A": 0.0, "B": 0.09, "C": 0.0},
    "C": {"A": 0.0, "B": 0.0, "C": 0.16},
}
TARGET_RETURN = 0.09
PORTFOLIO_VALUE = 1_000_000.0
CONFIDENCE_LEVEL = 0.95


def _base_achievable_var() -> float:
    """The real minimum achievable VaR at TARGET_RETURN, via minimize_variance itself."""
    base = minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN)
    return parametric_var(
        portfolio_value=PORTFOLIO_VALUE,
        portfolio_std_dev=base.result["portfolio_variance"] ** 0.5,
        confidence_level=CONFIDENCE_LEVEL,
    ).result


def test_non_binding_cap_matches_unconstrained_minimum_variance_result():
    base_var = _base_achievable_var()
    generous_cap = base_var * 2  # comfortably above what's achievable — should never bind

    capped = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=generous_cap,
        confidence_level=CONFIDENCE_LEVEL,
    )
    base = minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN)

    for asset in ASSET_ORDER:
        assert capped.result["weights"][asset] == pytest.approx(base.result["weights"][asset], abs=1e-5)
    assert capped.result["value_at_risk"] < generous_cap  # constraint clearly slack


def test_cap_exactly_at_achievable_minimum_is_tight_but_still_feasible():
    base_var = _base_achievable_var()

    capped = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=base_var,  # exactly at the boundary
        confidence_level=CONFIDENCE_LEVEL,
    )

    # The constraint is active (tight) at the solution — recomputed VaR
    # sits right at the cap, not comfortably below it.
    assert capped.result["value_at_risk"] == pytest.approx(base_var, rel=1e-4)


def test_loss_cap_below_achievable_var_rejects_a_candidate_minimize_variance_would_have_accepted():
    """
    The real "the cap changes the result" proof: minimize_variance
    happily returns a candidate at TARGET_RETURN. A cap set below that
    candidate's actual VaR makes minimize_variance_with_loss_cap refuse
    to return ANYTHING for the same target_return — proving the cap is
    enforced in the solver itself, not as a downstream check that would
    have let the same candidate through with a warning attached.
    """
    base = minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN)
    base_var = parametric_var(
        portfolio_value=PORTFOLIO_VALUE,
        portfolio_std_dev=base.result["portfolio_variance"] ** 0.5,
        confidence_level=CONFIDENCE_LEVEL,
    ).result
    assert base_var > 0  # sanity: minimize_variance really did accept this target_return

    tight_cap = base_var * 0.5  # below what's achievable — must be rejected

    with pytest.raises(ValueError, match="every portfolio achieving it violates the loss cap"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS,
            COVARIANCE,
            TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=tight_cap,
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_infeasibility_error_names_the_achievable_var_and_the_cap():
    base_var = _base_achievable_var()
    tight_cap = base_var * 0.1

    with pytest.raises(ValueError) as exc_info:
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS,
            COVARIANCE,
            TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=tight_cap,
            confidence_level=CONFIDENCE_LEVEL,
        )

    message = str(exc_info.value)
    assert str(tight_cap) in message
    assert "minimum achievable VaR" in message


def test_infeasible_base_constraints_reported_distinctly_from_loss_cap_infeasibility():
    """
    Distinguishes the two possible infeasibility causes: here
    target_return itself is outside what's achievable at all under the
    given weight bounds — infeasible before the loss cap is even
    considered — so the error must say so, not misattribute the failure
    to the loss cap.
    """
    unachievable_target_return = 100.0  # far outside [0.05, 0.12]

    with pytest.raises(ValueError, match="infeasible before the loss cap is even considered"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS,
            COVARIANCE,
            unachievable_target_return,
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=1_000_000.0,
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_recomputed_var_is_independently_confirmed_at_or_below_the_cap():
    base_var = _base_achievable_var()
    cap = base_var * 1.5

    result = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=cap,
        confidence_level=CONFIDENCE_LEVEL,
    )

    # Independently recomputed from the returned weights, via
    # quant-engine's own tested parametric_var — not trusting the
    # function's internal value_at_risk figure at face value.
    weights = result.result["weights"]
    variance = sum(
        weights[a] * weights[b] * COVARIANCE[a][b] for a in ASSET_ORDER for b in ASSET_ORDER
    )
    independently_recomputed_var = parametric_var(
        portfolio_value=PORTFOLIO_VALUE,
        portfolio_std_dev=variance**0.5,
        confidence_level=CONFIDENCE_LEVEL,
    ).result

    assert independently_recomputed_var <= cap + 1e-6
    assert independently_recomputed_var == pytest.approx(result.result["value_at_risk"], rel=1e-9)


def test_weights_sum_to_one_and_respect_bounds():
    result = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    total = sum(result.result["weights"].values())
    assert total == pytest.approx(1.0, abs=1e-6)
    for w in result.result["weights"].values():
        assert -1e-6 <= w <= 1.0 + 1e-6


def test_rejects_confidence_level_at_or_below_one_half():
    with pytest.raises(ValueError, match="must be > 0.5"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS,
            COVARIANCE,
            TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=1_000_000.0,
            confidence_level=0.5,
        )
