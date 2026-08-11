"""
Tests for the Capital Efficiency Score (QUANT_ENGINE_SPEC.md, Sections
7/8/9).

Cash, Risk, Tax, and Investment efficiency are spec-derived — tests
confirm exact formula results, hand-verified against Section 7's
formulas as re-read directly (not from memory/paraphrase). Debt and
Liquidity efficiency have no spec formula (Section 7 gives prose only)
and are DESIGNED here — tests confirm the DESIGNED behavior described in
their own docstrings (the 50-point breakeven, the asymmetric penalty),
not a spec formula, since none exists.
"""

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_quant import (
    cash_efficiency,
    composite_capital_efficiency_score,
    debt_efficiency,
    investment_efficiency,
    liquidity_efficiency,
    parametric_var,
    risk_efficiency,
    sharpe_ratio,
    tax_efficiency,
)
from optifi_quant.capital_efficiency import (
    _DEBT_EFFICIENCY_FULL_SWING_GAP,
    _LIQUIDITY_EXCESS_PENALTY_RATE,
    _LIQUIDITY_SHORTFALL_PENALTY_RATE,
)


def _upstream_uap(result) -> UAP:
    """A minimal, valid UAP standing in for some other engine's output,
    for tests that need to hand a pre-computed upstream value to a
    Capital Efficiency function (e.g. Investment efficiency's
    max_achievable_sharpe_ratio)."""
    return UAP(
        subject="test upstream value",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="test fixture",
        producer="test fixture",
        confidence=ConfidenceLevel.MODERATE,
    )


# --- cash_efficiency (QUANT_ENGINE_SPEC.md Section 7, spec-derived) ---


def test_cash_efficiency_normal_case_matches_spec_formula():
    # min(100, (0.04 / 0.05) * 100) = min(100, 80) = 80
    uap = cash_efficiency(achieved_yield_on_cash=0.04, best_available_comparable_yield=0.05)
    assert uap.result == pytest.approx(80.0)
    assert uap.information_class == InformationClass.ESTIMATE


def test_cash_efficiency_boundary_exactly_100():
    # achieved == comparable -> ratio 1.0 -> exactly 100, the spec's own
    # min(100, ...) ceiling landed on exactly, not exceeded.
    uap = cash_efficiency(achieved_yield_on_cash=0.05, best_available_comparable_yield=0.05)
    assert uap.result == pytest.approx(100.0)


def test_cash_efficiency_exceeding_100_is_clamped():
    # achieved is DOUBLE the comparable yield -> raw ratio would be 200,
    # confirming the min(100, ...) ceiling actually clamps rather than
    # merely never being exercised.
    uap = cash_efficiency(achieved_yield_on_cash=0.10, best_available_comparable_yield=0.05)
    assert uap.result == pytest.approx(100.0)


def test_cash_efficiency_negative_yield_floored_at_zero():
    # A negative achieved yield (fees exceeding interest) would produce a
    # negative raw score under the spec's literal formula; Section 9's
    # separate 0-100 bound floors it at 0.
    uap = cash_efficiency(achieved_yield_on_cash=-0.02, best_available_comparable_yield=0.05)
    assert uap.result == pytest.approx(0.0)


def test_cash_efficiency_raises_on_zero_comparable_yield():
    with pytest.raises(ValueError):
        cash_efficiency(achieved_yield_on_cash=0.04, best_available_comparable_yield=0.0)


# --- debt_efficiency (QUANT_ENGINE_SPEC.md Section 7 — DESIGNED, no spec formula) ---


def test_debt_efficiency_at_breakeven_is_exactly_fifty():
    # return == cost -> gap == 0 -> score == 50, by construction.
    uap = debt_efficiency(effective_borrowing_cost=0.06, risk_adjusted_expected_return=0.06)
    assert uap.result == pytest.approx(50.0)


def test_debt_efficiency_below_breakeven_scores_under_fifty():
    # cost (0.10) exceeds return (0.06) -> inefficient -> score < 50.
    uap = debt_efficiency(effective_borrowing_cost=0.10, risk_adjusted_expected_return=0.06)
    gap = 0.06 - 0.10
    expected = 50.0 + (gap / _DEBT_EFFICIENCY_FULL_SWING_GAP) * 50.0
    assert uap.result == pytest.approx(expected)
    assert uap.result < 50.0


def test_debt_efficiency_above_breakeven_scores_over_fifty():
    # return (0.10) exceeds cost (0.06) -> efficient -> score > 50.
    uap = debt_efficiency(effective_borrowing_cost=0.06, risk_adjusted_expected_return=0.10)
    gap = 0.10 - 0.06
    expected = 50.0 + (gap / _DEBT_EFFICIENCY_FULL_SWING_GAP) * 50.0
    assert uap.result == pytest.approx(expected)
    assert uap.result > 50.0


def test_debt_efficiency_boundary_exactly_100_at_full_swing_gap():
    # gap == +_DEBT_EFFICIENCY_FULL_SWING_GAP exactly -> saturates to 100.
    uap = debt_efficiency(
        effective_borrowing_cost=0.05,
        risk_adjusted_expected_return=0.05 + _DEBT_EFFICIENCY_FULL_SWING_GAP,
    )
    assert uap.result == pytest.approx(100.0)


def test_debt_efficiency_boundary_exactly_0_at_full_swing_gap():
    # gap == -_DEBT_EFFICIENCY_FULL_SWING_GAP exactly -> saturates to 0.
    uap = debt_efficiency(
        effective_borrowing_cost=0.05 + _DEBT_EFFICIENCY_FULL_SWING_GAP,
        risk_adjusted_expected_return=0.05,
    )
    assert uap.result == pytest.approx(0.0, abs=1e-9)


def test_debt_efficiency_exceeding_full_swing_gap_is_clamped():
    # A gap far beyond the full-swing threshold in both directions
    # confirms clamping actually engages, not just reaches the boundary.
    high = debt_efficiency(effective_borrowing_cost=0.02, risk_adjusted_expected_return=0.50)
    low = debt_efficiency(effective_borrowing_cost=0.50, risk_adjusted_expected_return=0.02)
    assert high.result == pytest.approx(100.0)
    assert low.result == pytest.approx(0.0)


def test_debt_efficiency_docstring_marks_it_as_designed_not_spec_derived():
    uap = debt_efficiency(effective_borrowing_cost=0.05, risk_adjusted_expected_return=0.05)
    assert "DESIGNED" in debt_efficiency.__doc__
    assert "DESIGNED" in uap.producer


# --- risk_efficiency (QUANT_ENGINE_SPEC.md Section 7, spec-derived; uses parametric_var) ---


def test_risk_efficiency_normal_case_matches_spec_formula():
    portfolio_value = 1_000_000.0
    portfolio_std_dev = 0.10
    confidence_level = 0.95
    realised_risk = parametric_var(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
    ).result
    target_risk = realised_risk * 1.5  # deliberately off-target

    uap = risk_efficiency(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
        target_risk=target_risk,
    )
    expected = 100.0 - (abs(realised_risk - target_risk) / target_risk) * 100.0
    assert uap.result == pytest.approx(expected)


def test_risk_efficiency_boundary_exactly_100_when_realised_equals_target():
    portfolio_value = 1_000_000.0
    portfolio_std_dev = 0.10
    confidence_level = 0.95
    realised_risk = parametric_var(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
    ).result

    uap = risk_efficiency(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
        target_risk=realised_risk,
    )
    assert uap.result == pytest.approx(100.0)


def test_risk_efficiency_extreme_deviation_is_floored_at_zero():
    # target_risk vastly smaller than realised_risk -> raw score deeply
    # negative under the spec's literal formula; floored at 0.
    uap = risk_efficiency(
        portfolio_value=1_000_000.0,
        portfolio_std_dev=0.10,
        confidence_level=0.95,
        target_risk=1.0,
    )
    assert uap.result == pytest.approx(0.0)


def test_risk_efficiency_raises_on_zero_target_risk():
    with pytest.raises(ValueError):
        risk_efficiency(
            portfolio_value=1_000_000.0, portfolio_std_dev=0.10, confidence_level=0.95, target_risk=0.0
        )


def test_risk_efficiency_uses_parametric_var_and_records_its_dependency():
    portfolio_value = 1_000_000.0
    portfolio_std_dev = 0.10
    confidence_level = 0.95
    expected_realised_risk = parametric_var(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
    ).result

    uap = risk_efficiency(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
        target_risk=expected_realised_risk,
    )
    # The realised_risk parametric_var UAP's id must be a recorded dependency.
    assert len(uap.dependencies) == 1


# --- tax_efficiency (QUANT_ENGINE_SPEC.md Section 7, spec-derived) ---


def test_tax_efficiency_normal_case_matches_spec_formula():
    uap = tax_efficiency(tax_advantaged_allocation_used=15_000, tax_advantaged_allocation_available=20_000)
    assert uap.result == pytest.approx(75.0)


def test_tax_efficiency_boundary_exactly_100_when_fully_utilised():
    uap = tax_efficiency(tax_advantaged_allocation_used=20_000, tax_advantaged_allocation_available=20_000)
    assert uap.result == pytest.approx(100.0)


def test_tax_efficiency_boundary_exactly_0_when_unused():
    uap = tax_efficiency(tax_advantaged_allocation_used=0, tax_advantaged_allocation_available=20_000)
    assert uap.result == pytest.approx(0.0)


def test_tax_efficiency_used_exceeding_available_is_clamped():
    # Shouldn't occur with internally-consistent inputs, but confirms
    # the Section-9-mandated ceiling actually engages if it does.
    uap = tax_efficiency(tax_advantaged_allocation_used=30_000, tax_advantaged_allocation_available=20_000)
    assert uap.result == pytest.approx(100.0)


def test_tax_efficiency_raises_on_zero_available():
    with pytest.raises(ValueError):
        tax_efficiency(tax_advantaged_allocation_used=1_000, tax_advantaged_allocation_available=0.0)


# --- liquidity_efficiency (QUANT_ENGINE_SPEC.md Section 7 — DESIGNED, asymmetric) ---


def test_liquidity_efficiency_at_reserve_is_exactly_100():
    uap = liquidity_efficiency(actual_cash=100_000, minimum_cash_reserve=100_000)
    assert uap.result == pytest.approx(100.0)


def test_liquidity_efficiency_below_reserve_matches_shortfall_formula():
    # 20% below reserve.
    uap = liquidity_efficiency(actual_cash=80_000, minimum_cash_reserve=100_000)
    expected = 100.0 - 0.20 * _LIQUIDITY_SHORTFALL_PENALTY_RATE
    assert uap.result == pytest.approx(max(0.0, expected))


def test_liquidity_efficiency_above_reserve_matches_excess_formula():
    # 20% above reserve.
    uap = liquidity_efficiency(actual_cash=120_000, minimum_cash_reserve=100_000)
    expected = 100.0 - 0.20 * _LIQUIDITY_EXCESS_PENALTY_RATE
    assert uap.result == pytest.approx(max(0.0, expected))


def test_liquidity_efficiency_asymmetric_penalty_is_real():
    """
    The core requirement: an equal-MAGNITUDE shortfall must score LOWER
    than an equal-magnitude surplus — not merely described as asymmetric
    in the docstring, but actually numerically different.
    """
    below = liquidity_efficiency(actual_cash=70_000, minimum_cash_reserve=100_000)  # 30% short
    above = liquidity_efficiency(actual_cash=130_000, minimum_cash_reserve=100_000)  # 30% over
    assert below.result < above.result
    # And confirm it isn't just "different" but specifically follows the
    # documented 3x-steeper shortfall rate.
    assert _LIQUIDITY_SHORTFALL_PENALTY_RATE > _LIQUIDITY_EXCESS_PENALTY_RATE
    expected_below = max(0.0, 100.0 - 0.30 * _LIQUIDITY_SHORTFALL_PENALTY_RATE)
    expected_above = max(0.0, 100.0 - 0.30 * _LIQUIDITY_EXCESS_PENALTY_RATE)
    assert below.result == pytest.approx(expected_below)
    assert above.result == pytest.approx(expected_above)


def test_liquidity_efficiency_large_shortfall_floored_at_zero():
    uap = liquidity_efficiency(actual_cash=0.0, minimum_cash_reserve=100_000)
    assert uap.result == pytest.approx(0.0)


def test_liquidity_efficiency_large_excess_floored_at_zero_not_negative():
    # A large enough excess also drives the raw score below 0 under this
    # formula (100 - relative_deviation * rate can go negative); confirms
    # it's clamped, not reported as negative.
    uap = liquidity_efficiency(actual_cash=300_000, minimum_cash_reserve=100_000)  # 200% over
    assert uap.result == pytest.approx(0.0)


def test_liquidity_efficiency_raises_on_zero_reserve():
    with pytest.raises(ValueError):
        liquidity_efficiency(actual_cash=10_000, minimum_cash_reserve=0.0)


def test_liquidity_efficiency_docstring_marks_it_as_designed_not_spec_derived():
    uap = liquidity_efficiency(actual_cash=100_000, minimum_cash_reserve=100_000)
    assert "DESIGNED" in liquidity_efficiency.__doc__
    assert "DESIGNED" in uap.producer


# --- investment_efficiency (QUANT_ENGINE_SPEC.md Section 7, spec-derived) ---


def test_investment_efficiency_normal_case_matches_spec_formula():
    portfolio_return, risk_free_rate, portfolio_std_dev = 0.08, 0.03, 0.12
    achieved_sharpe = (portfolio_return - risk_free_rate) / portfolio_std_dev
    max_sharpe_uap = _upstream_uap(achieved_sharpe * 2.0)  # frontier does meaningfully better

    uap = investment_efficiency(
        portfolio_return=portfolio_return,
        risk_free_rate=risk_free_rate,
        portfolio_std_dev=portfolio_std_dev,
        max_achievable_sharpe_ratio=max_sharpe_uap,
    )
    expected = (achieved_sharpe / (achieved_sharpe * 2.0)) * 100.0
    assert uap.result == pytest.approx(expected)
    assert uap.result == pytest.approx(50.0)


def test_investment_efficiency_boundary_exactly_100_when_achieved_equals_max():
    portfolio_return, risk_free_rate, portfolio_std_dev = 0.08, 0.03, 0.12
    achieved_sharpe = (portfolio_return - risk_free_rate) / portfolio_std_dev
    max_sharpe_uap = _upstream_uap(achieved_sharpe)  # portfolio IS on the frontier

    uap = investment_efficiency(
        portfolio_return=portfolio_return,
        risk_free_rate=risk_free_rate,
        portfolio_std_dev=portfolio_std_dev,
        max_achievable_sharpe_ratio=max_sharpe_uap,
    )
    assert uap.result == pytest.approx(100.0)


def test_investment_efficiency_exceeding_100_is_clamped():
    # A max_achievable_sharpe_ratio SMALLER than the achieved Sharpe
    # (shouldn't occur if the frontier value is genuinely maximal, but
    # confirms the ceiling actually engages).
    portfolio_return, risk_free_rate, portfolio_std_dev = 0.08, 0.03, 0.12
    achieved_sharpe = (portfolio_return - risk_free_rate) / portfolio_std_dev
    max_sharpe_uap = _upstream_uap(achieved_sharpe * 0.5)

    uap = investment_efficiency(
        portfolio_return=portfolio_return,
        risk_free_rate=risk_free_rate,
        portfolio_std_dev=portfolio_std_dev,
        max_achievable_sharpe_ratio=max_sharpe_uap,
    )
    assert uap.result == pytest.approx(100.0)


def test_investment_efficiency_raises_on_zero_max_sharpe():
    with pytest.raises(ValueError):
        investment_efficiency(
            portfolio_return=0.08,
            risk_free_rate=0.03,
            portfolio_std_dev=0.12,
            max_achievable_sharpe_ratio=_upstream_uap(0.0),
        )


def test_investment_efficiency_records_optimisation_engine_dependency():
    """
    Code Quality requirement: optimisation-engine's output id must
    appear in the returned UAP's `dependencies` field
    (QUANT_ENGINE_SPEC.md Section 7's explicit instruction).
    """
    max_sharpe_uap = _upstream_uap(1.0)
    uap = investment_efficiency(
        portfolio_return=0.08,
        risk_free_rate=0.03,
        portfolio_std_dev=0.12,
        max_achievable_sharpe_ratio=max_sharpe_uap,
    )
    assert max_sharpe_uap.id in uap.dependencies


# --- composite_capital_efficiency_score (QUANT_ENGINE_SPEC.md Section 8) ---


def test_composite_uses_equal_weighting():
    scores = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    uaps = [_upstream_uap(s) for s in scores]
    composite = composite_capital_efficiency_score(*uaps)
    expected = sum(scores) / 6.0
    assert composite.result == pytest.approx(expected)
    assert composite.information_class == InformationClass.ESTIMATE


def test_composite_validates_to_0_100_bound():
    uaps = [_upstream_uap(s) for s in [0.0, 100.0, 50.0, 25.0, 75.0, 60.0]]
    composite = composite_capital_efficiency_score(*uaps)
    assert 0.0 <= composite.result <= 100.0


def test_composite_assumptions_state_weighting_is_provisional():
    uaps = [_upstream_uap(50.0) for _ in range(6)]
    composite = composite_capital_efficiency_score(*uaps)
    joined = " ".join(composite.assumptions)
    assert "PROVISIONAL" in joined
    assert "equal weighting" in joined.lower()


def test_composite_all_six_at_maximum_extreme_lands_at_100():
    uaps = [_upstream_uap(100.0) for _ in range(6)]
    composite = composite_capital_efficiency_score(*uaps)
    assert composite.result == pytest.approx(100.0)


def test_composite_all_six_at_minimum_extreme_lands_at_0():
    uaps = [_upstream_uap(0.0) for _ in range(6)]
    composite = composite_capital_efficiency_score(*uaps)
    assert composite.result == pytest.approx(0.0)


def test_composite_mixed_extremes_still_correctly_bounded():
    # Three sub-scores at 0, three at 100 -> equal-weighted average = 50,
    # still comfortably inside [0, 100].
    uaps = [_upstream_uap(0.0)] * 3 + [_upstream_uap(100.0)] * 3
    composite = composite_capital_efficiency_score(*uaps)
    assert composite.result == pytest.approx(50.0)
    assert 0.0 <= composite.result <= 100.0


def test_composite_raises_if_a_sub_score_is_out_of_bound():
    # A malformed/out-of-contract sub-score UAP (e.g. from a bug
    # elsewhere) must be rejected explicitly here, not silently averaged
    # in — Section 9's precondition, enforced as a real check.
    bad_uaps = [_upstream_uap(50.0)] * 5 + [_upstream_uap(150.0)]
    with pytest.raises(ValueError):
        composite_capital_efficiency_score(*bad_uaps)


def test_composite_records_all_six_sub_score_dependencies():
    uaps = [_upstream_uap(50.0) for _ in range(6)]
    composite = composite_capital_efficiency_score(*uaps)
    for uap in uaps:
        assert uap.id in composite.dependencies
    assert len(composite.dependencies) == 6
