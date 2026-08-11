"""
Tests for verify_optimisation_candidate and verify_loss_cap_candidate
(VERIFICATION_FRAMEWORK.md, Section 5.5).
"""

from optifi_quant import parametric_var, portfolio_variance

from optifi_verification import (
    FailureCategory,
    VerdictType,
    verify_loss_cap_candidate,
    verify_optimisation_candidate,
)

EXPECTED_RETURNS = {"A": 0.05, "B": 0.10}
COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0},
    "B": {"A": 0.0, "B": 0.09},
}


# --- verify_optimisation_candidate ---


def test_valid_candidate_passes():
    weights = {"A": 0.6, "B": 0.4}
    target_return = 0.6 * 0.05 + 0.4 * 0.10  # 0.07
    verdict = verify_optimisation_candidate(
        weights, EXPECTED_RETURNS, target_return, min_weight=0.0, max_weight=1.0
    )
    assert verdict.verdict_type == VerdictType.PASS
    # Content of the PASS verdict's own reasons, not just its type.
    assert verdict.reasons == [
        "weights sum to 1, respect bounds, and achieve target_return within tolerance"
    ]


def test_weight_sum_violation_rejects():
    weights = {"A": 0.6, "B": 0.5}  # sums to 1.1
    verdict = verify_optimisation_candidate(
        weights, EXPECTED_RETURNS, target_return=0.08, min_weight=0.0, max_weight=1.0
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert any("sum to" in reason for reason in verdict.reasons)
    assert verdict.failure_category == FailureCategory.DATA_QUALITY


def test_bounds_violation_rejects():
    weights = {"A": 0.9, "B": 0.1}  # sums to 1.0, but A exceeds max_weight
    target_return = 0.9 * 0.05 + 0.1 * 0.10  # matches these weights exactly
    verdict = verify_optimisation_candidate(
        weights, EXPECTED_RETURNS, target_return, min_weight=0.0, max_weight=0.8
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert any("outside bounds" in reason for reason in verdict.reasons)
    assert verdict.failure_category == FailureCategory.DATA_QUALITY


def test_target_return_mismatch_rejects():
    weights = {"A": 0.6, "B": 0.4}  # actual achieved return is 0.07
    verdict = verify_optimisation_candidate(
        weights, EXPECTED_RETURNS, target_return=0.10, min_weight=0.0, max_weight=1.0
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert any("does not match target_return" in reason for reason in verdict.reasons)


def test_multiple_simultaneous_failures_all_reported():
    weights = {"A": 0.6, "B": 0.5}  # sums to 1.1, and B exceeds max_weight
    target_return = 0.6 * 0.05 + 0.5 * 0.10  # matches these (invalid) weights exactly
    verdict = verify_optimisation_candidate(
        weights, EXPECTED_RETURNS, target_return, min_weight=0.0, max_weight=0.45
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert any("sum to" in reason for reason in verdict.reasons)
    assert any("outside bounds" in reason for reason in verdict.reasons)
    assert len(verdict.reasons) >= 2


def test_candidate_with_unrecognized_asset_is_rejected_not_silently_zeroed():
    """
    Code Quality Verification finding #3: a weight for an asset absent
    from expected_returns must be flagged by name, not silently treated
    as contributing 0.0 to achieved_return.
    """
    weights = {"A": 0.5, "B": 0.3, "C": 0.2}  # "C" has no entry in EXPECTED_RETURNS
    # Chosen so that IF "C" were silently zeroed, achieved_return would
    # still match target_return exactly — proving this candidate is
    # rejected because of the unrecognized asset itself, not because of
    # an incidental target_return mismatch.
    target_return = 0.5 * 0.05 + 0.3 * 0.10

    verdict = verify_optimisation_candidate(weights, EXPECTED_RETURNS, target_return, min_weight=0.0, max_weight=1.0)

    assert verdict.verdict_type == VerdictType.REJECT
    assert any("'C'" in reason and "expected_returns" in reason for reason in verdict.reasons)
    # No misleading target_return-mismatch reason — that check is
    # correctly skipped since achieved_return can't be meaningfully
    # computed while an asset is unrecognized.
    assert not any("does not match target_return" in reason for reason in verdict.reasons)


def test_candidate_with_all_assets_recognized_is_unaffected_by_the_fix():
    """Control case: normal candidates referencing only known assets are unaffected."""
    weights = {"A": 0.6, "B": 0.4}
    target_return = 0.6 * 0.05 + 0.4 * 0.10
    verdict = verify_optimisation_candidate(weights, EXPECTED_RETURNS, target_return, min_weight=0.0, max_weight=1.0)
    assert verdict.verdict_type == VerdictType.PASS


# --- verify_loss_cap_candidate ---

_VALID_WEIGHTS = {"A": 0.6, "B": 0.4}
_TARGET_RETURN = 0.6 * 0.05 + 0.4 * 0.10  # 0.07
_PORTFOLIO_VALUE = 100_000.0
_CONFIDENCE_LEVEL = 0.95


def _real_var_for(weights: dict[str, float]) -> float:
    """The actual VaR quant-engine computes for `weights`, used to derive test cap values."""
    pv = portfolio_variance(weights, COVARIANCE)
    return parametric_var(
        portfolio_value=_PORTFOLIO_VALUE,
        portfolio_std_dev=pv.result**0.5,
        confidence_level=_CONFIDENCE_LEVEL,
    ).result


def test_valid_candidate_within_cap_passes():
    real_var = _real_var_for(_VALID_WEIGHTS)
    verdict = verify_loss_cap_candidate(
        _VALID_WEIGHTS,
        EXPECTED_RETURNS,
        COVARIANCE,
        _TARGET_RETURN,
        portfolio_value=_PORTFOLIO_VALUE,
        max_single_period_loss=real_var + 1000,  # comfortably above the real VaR
        confidence_level=_CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    assert verdict.verdict_type == VerdictType.PASS
    # Content of the PASS verdict's own reasons, not just its type.
    assert verdict.reasons == [
        "weights sum to 1, respect bounds, achieve target_return, and "
        "recomputed VaR is within max_single_period_loss"
    ]


def test_hand_constructed_candidate_violating_cap_is_rejected():
    """
    A candidate not produced by the real solver, deliberately violating a
    tight loss cap. The rejection reason must name the VaR breach
    specifically.
    """
    real_var = _real_var_for(_VALID_WEIGHTS)
    verdict = verify_loss_cap_candidate(
        _VALID_WEIGHTS,
        EXPECTED_RETURNS,
        COVARIANCE,
        _TARGET_RETURN,
        portfolio_value=_PORTFOLIO_VALUE,
        max_single_period_loss=real_var - 1000,  # deliberately below the real VaR
        confidence_level=_CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert any(
        "recomputed parametric VaR" in reason and "exceeds max_single_period_loss" in reason
        for reason in verdict.reasons
    )
    assert verdict.failure_category == FailureCategory.DATA_QUALITY


def test_candidate_failing_both_cap_and_weight_sum_reports_both():
    invalid_weights = {"A": 0.6, "B": 0.5}  # sums to 1.1
    real_var = _real_var_for(_VALID_WEIGHTS)  # a tight cap, well below any plausible VaR
    verdict = verify_loss_cap_candidate(
        invalid_weights,
        EXPECTED_RETURNS,
        COVARIANCE,
        target_return=0.6 * 0.05 + 0.5 * 0.10,
        portfolio_value=_PORTFOLIO_VALUE,
        max_single_period_loss=1.0,  # essentially zero tolerance for any loss
        confidence_level=_CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert any("sum to" in reason for reason in verdict.reasons)
    # quant-engine's own portfolio_variance rejects weights not summing to
    # 1, so the independent VaR check surfaces as a second, distinct
    # failure rather than silently succeeding on malformed input.
    assert any("could not independently recompute VaR" in reason for reason in verdict.reasons)
    assert len(verdict.reasons) >= 2
    assert real_var > 0  # sanity: real_var was actually computed, not skipped


def test_boundary_case_at_cap_within_tolerance_is_not_falsely_rejected():
    real_var = _real_var_for(_VALID_WEIGHTS)
    verdict = verify_loss_cap_candidate(
        _VALID_WEIGHTS,
        EXPECTED_RETURNS,
        COVARIANCE,
        _TARGET_RETURN,
        portfolio_value=_PORTFOLIO_VALUE,
        max_single_period_loss=real_var,  # exactly at the cap
        confidence_level=_CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
        tolerance=1e-6,
    )
    assert verdict.verdict_type == VerdictType.PASS
