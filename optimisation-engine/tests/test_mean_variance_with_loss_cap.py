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
from optifi_optimisation.mean_variance import _LOSS_CAP_REVERIFICATION_TOLERANCE

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


# --- Code Quality Verification fixes: #1/#2 ---


def test_loss_cap_reverification_tolerance_is_pinned():
    """
    Pins the exact tolerance value, not just its existence — the code
    quality report's mutation testing found that this constant could be
    changed by six orders of magnitude (1e-6 -> 1.000001) with nothing
    noticing. This test alone won't catch a silent behavioral regression
    (see the next test for that), but it directly catches the constant
    itself being changed, accidentally or otherwise.
    """
    assert _LOSS_CAP_REVERIFICATION_TOLERANCE == 1e-6


def test_final_reverification_guard_actually_fires_when_solver_output_is_wrong(monkeypatch):
    """
    THE key test from the code quality report: directly exercises the
    final internal re-verification guard (mean_variance.py's line
    checking `value_at_risk > max_single_period_loss +
    _LOSS_CAP_REVERIFICATION_TOLERANCE`) actually mattering. In real
    operation this guard should never fire, because the solver's own
    quad_form constraint already enforces the cap — that's exactly why
    it was never covered by any existing test. To prove the guard itself
    works, this simulates what would happen if the solver's constraint
    satisfaction were ever wrong (numerical drift, a future refactor
    bug) by monkeypatching parametric_var — the function this guard
    calls to recompute VaR from the solved weights — to report a wildly
    inflated value, independent of what the solver actually did.
    """
    import optifi_optimisation.mean_variance as mean_variance_module

    class _InflatedVarResult:
        result = 999_999_999.0

    monkeypatch.setattr(
        mean_variance_module,
        "parametric_var",
        lambda *args, **kwargs: _InflatedVarResult(),
    )

    # A generous cap that would ordinarily be comfortably satisfied —
    # the only reason this raises is the monkeypatched inflated VaR.
    with pytest.raises(ValueError, match="recomputed VaR"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS,
            COVARIANCE,
            TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=1_000_000.0,
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_final_reverification_guard_is_strictly_greater_than_not_greater_or_equal(monkeypatch):
    """
    Precise boundary test for the guard's comparison operator itself
    (`>` not `>=`): monkeypatches parametric_var to report a VaR that
    lands EXACTLY at max_single_period_loss + tolerance — the guard must
    NOT fire at that exact boundary, only strictly beyond it. A cap
    comfortably above the achievable VaR (as in the test above) can't
    distinguish `>` from `>=`; only an exact-boundary value can.
    """
    import optifi_optimisation.mean_variance as mean_variance_module

    cap = 1_000_000.0
    exact_boundary = cap + mean_variance_module._LOSS_CAP_REVERIFICATION_TOLERANCE

    class _ExactBoundaryVarResult:
        result = exact_boundary

    monkeypatch.setattr(
        mean_variance_module,
        "parametric_var",
        lambda *args, **kwargs: _ExactBoundaryVarResult(),
    )

    # Must NOT raise: exactly at the boundary is still within tolerance.
    result = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=cap,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert result.result["value_at_risk"] == exact_boundary


def test_reverification_guard_does_not_fire_on_a_genuinely_valid_result():
    """
    Control case for the mocked test above: confirms the guard doesn't
    spuriously fire on an honest, unmocked solve — otherwise the
    monkeypatched test above would be trivially "passing" for the wrong
    reason (a guard that always fires, mocked or not).
    """
    result = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=1_000_000.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert result.result["value_at_risk"] <= 1_000_000.0


# --- Code Quality Verification fixes: the four untested input-validation guards ---


def test_confidence_level_zero_raises():
    with pytest.raises(ValueError, match="strictly between 0 and 1"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE, max_single_period_loss=1_000_000.0,
            confidence_level=0.0,
        )


def test_confidence_level_one_raises():
    """
    Exact upper boundary (1.0, not 1.5): must be rejected by this
    function's OWN guard, `0 < confidence_level < 1`. A loose match on
    just "strictly between 0 and 1" is not sufficient here — if the
    guard were mutated to `0 < confidence_level <= 1`, 1.0 would pass it
    and fall through to `norm.ppf(1.0)` = inf downstream in
    quant-engine's parametric_var, which raises its OWN, differently-
    scoped "confidence_level must be strictly between 0 and 1" error —
    coincidentally matching the same loose regex and masking the
    mutation. Matching this function's own message prefix (which
    parametric_var's message does not share) distinguishes the two.
    """
    with pytest.raises(
        ValueError,
        match="minimize_variance_with_loss_cap: confidence_level must be",
    ):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE, max_single_period_loss=1_000_000.0,
            confidence_level=1.0,
        )


def test_confidence_level_above_one_raises():
    with pytest.raises(ValueError, match="strictly between 0 and 1"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE, max_single_period_loss=1_000_000.0,
            confidence_level=1.5,
        )


def test_portfolio_value_zero_raises():
    with pytest.raises(ValueError, match="portfolio_value must be positive"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=0.0, max_single_period_loss=1_000_000.0,
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_portfolio_value_negative_raises():
    with pytest.raises(ValueError, match="portfolio_value must be positive"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=-100.0, max_single_period_loss=1_000_000.0,
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_portfolio_value_at_one_passes_this_specific_guard():
    """
    Boundary precision for `portfolio_value <= 0`: portfolio_value=1.0
    is NOT rejected by this guard — only portfolio_value=0.0 or below
    is. This distinguishes the real guard from a mutant
    `portfolio_value <= 1`, which would incorrectly reject 1.0 too.
    max_single_period_loss is scaled down to 1.0 in step with
    portfolio_value (keeping the same ratio as the suite's standard
    1,000,000/1,000,000 cases) — using a tiny portfolio_value with a
    disproportionately huge cap produces a badly-scaled, numerically
    unstable problem for the solver (empirically verified to raise
    cvxpy.error.SolverError rather than exercising this guard at all),
    which isn't what this test is trying to check.
    """
    result = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
        portfolio_value=1.0, max_single_period_loss=1.0,
        confidence_level=CONFIDENCE_LEVEL,
    )
    assert abs(sum(result.result["weights"].values()) - 1.0) < 1e-4


def test_max_single_period_loss_negative_raises():
    with pytest.raises(ValueError, match="must be non-negative"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE, max_single_period_loss=-1.0,
            confidence_level=CONFIDENCE_LEVEL,
        )


def test_max_single_period_loss_zero_passes_this_specific_guard():
    """
    Zero is explicitly allowed by this guard (only negative is
    rejected) — confirms we get past it. A zero-variance requirement
    may then correctly fail as infeasible for this non-trivial
    target_return, but that would be a DIFFERENT error (infeasibility),
    not this validation guard — so this test only asserts the specific
    "must be non-negative" message never appears, not that the overall
    call succeeds.
    """
    with pytest.raises(ValueError) as exc_info:
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE, max_single_period_loss=0.0,
            confidence_level=CONFIDENCE_LEVEL,
        )
    assert "must be non-negative" not in str(exc_info.value)


def test_min_weight_greater_than_max_weight_raises():
    with pytest.raises(ValueError, match="must not exceed max_weight"):
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE, max_single_period_loss=1_000_000.0,
            confidence_level=CONFIDENCE_LEVEL,
            min_weight=0.6, max_weight=0.4,
        )


def test_min_weight_equal_to_max_weight_passes_this_specific_guard():
    """
    Exact boundary for `min_weight > max_weight`: equal bounds must NOT
    trip this guard (only min_weight strictly greater than max_weight
    should). 0.6 > 0.4 in the test above doesn't distinguish `>` from a
    mutant `>=`, since both would raise identically for that input —
    only min_weight == max_weight can distinguish them. Equal bounds
    pin every weight to exactly 1/3 each (three assets, weights must sum
    to 1), which may then legitimately fail a DIFFERENT check (the
    resulting fixed portfolio's return may not equal target_return, or
    its VaR may exceed the cap) — so this only asserts the specific
    "must not exceed max_weight" message is absent, not that the call
    succeeds outright.
    """
    with pytest.raises(ValueError) as exc_info:
        minimize_variance_with_loss_cap(
            EXPECTED_RETURNS, COVARIANCE, TARGET_RETURN,
            portfolio_value=PORTFOLIO_VALUE, max_single_period_loss=1_000_000.0,
            confidence_level=CONFIDENCE_LEVEL,
            min_weight=1.0 / 3.0, max_weight=1.0 / 3.0,
        )
    assert "must not exceed max_weight" not in str(exc_info.value)
