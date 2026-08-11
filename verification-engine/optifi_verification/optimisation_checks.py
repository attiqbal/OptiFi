"""
Independent checks on optimisation-engine candidates —
VERIFICATION_FRAMEWORK.md Section 5.5: "for Stage 10 candidates
specifically, independently re-derive whether the candidate actually
respects the constraints it claims to, rather than trusting
optimisation-engine's own 'Constraints: PASS' self-report."

Neither function here calls optimisation-engine's solver or any of its
internal constraint-enforcement code — both re-derive everything from
first principles (or, for the VaR check, from quant-engine's
independently-tested formulas), which is what makes this genuinely
independent rather than an echo of the solver's own claim.
"""

from __future__ import annotations

from optifi_quant import parametric_var, portfolio_variance

from .verdict import FailureCategory, Verdict, VerdictType


def verify_optimisation_candidate(
    weights: dict[str, float],
    expected_returns: dict[str, float],
    target_return: float,
    min_weight: float,
    max_weight: float,
    tolerance: float = 1e-6,
) -> Verdict:
    """
    Independently re-derive whether `weights` actually satisfies the
    constraints an optimisation-engine candidate claims to:
    - weights sum to 1
    - every weight is within [min_weight, max_weight]
    - every asset in `weights` has a corresponding entry in `expected_returns`
    - the weighted expected return matches target_return

    All violated checks are reported together, not just the first found.

    Code Quality Verification finding #3: a `weights` entry for an asset
    absent from `expected_returns` used to be silently treated as
    contributing 0.0 to achieved_return (`expected_returns.get(asset,
    0.0)`) — a malformed candidate referencing an unrecognized asset
    could pass this check by coincidence rather than being caught. That
    asset is now flagged by name as its own failure, and achieved_return
    is not computed against a partially-defined expected_returns at all
    (it would be meaningless), so this specific check is skipped rather
    than reported as a possibly-misleading target_return mismatch.
    """
    reasons: list[str] = []

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > tolerance:
        reasons.append(
            f"weights sum to {weight_sum!r}, not within tolerance "
            f"({tolerance}) of 1.0"
        )

    for asset, weight in weights.items():
        if weight < min_weight - tolerance or weight > max_weight + tolerance:
            reasons.append(
                f"asset '{asset}' weight {weight!r} is outside bounds "
                f"[{min_weight}, {max_weight}]"
            )

    unrecognized_assets = sorted(asset for asset in weights if asset not in expected_returns)
    if unrecognized_assets:
        reasons.append(
            f"weights reference asset(s) with no entry in expected_returns, "
            f"so achieved return cannot be verified: {unrecognized_assets}"
        )
    else:
        achieved_return = sum(
            weight * expected_returns[asset] for asset, weight in weights.items()
        )
        if abs(achieved_return - target_return) > tolerance:
            reasons.append(
                f"achieved return {achieved_return!r} does not match "
                f"target_return {target_return!r} within tolerance ({tolerance})"
            )

    if reasons:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=reasons,
            failure_category=FailureCategory.DATA_QUALITY,
        )
    return Verdict(
        verdict_type=VerdictType.PASS,
        reasons=[
            "weights sum to 1, respect bounds, and achieve target_return "
            "within tolerance"
        ],
    )


def verify_loss_cap_candidate(
    weights: dict[str, float],
    expected_returns: dict[str, float],
    covariance: dict[str, dict[str, float]],
    target_return: float,
    portfolio_value: float,
    max_single_period_loss: float,
    confidence_level: float,
    min_weight: float,
    max_weight: float,
    tolerance: float = 1e-6,
) -> Verdict:
    """
    Runs every check `verify_optimisation_candidate` does, plus an
    independent recomputation of the candidate's parametric VaR — reusing
    quant-engine's own `portfolio_variance` and `parametric_var`
    directly, never reimplementing either formula, and never calling
    optimisation-engine's solver.

    If `portfolio_variance`/`parametric_var` themselves reject the
    candidate (e.g. because the weights are malformed enough that
    quant-engine's own guardrails fire), that failure is reported as an
    additional reason rather than raised as an unhandled exception — so a
    candidate that is broken in multiple ways still reports every
    failure, consistent with `verify_optimisation_candidate`'s behaviour.
    """
    base_verdict = verify_optimisation_candidate(
        weights, expected_returns, target_return, min_weight, max_weight, tolerance
    )
    reasons: list[str] = (
        list(base_verdict.reasons) if base_verdict.verdict_type == VerdictType.REJECT else []
    )

    try:
        pv_uap = portfolio_variance(weights, covariance)
        portfolio_std_dev = pv_uap.result**0.5
        var_uap = parametric_var(
            portfolio_value=portfolio_value,
            portfolio_std_dev=portfolio_std_dev,
            confidence_level=confidence_level,
        )
        recomputed_var = var_uap.result
        if recomputed_var > max_single_period_loss + tolerance:
            reasons.append(
                f"recomputed parametric VaR ({recomputed_var!r}) exceeds "
                f"max_single_period_loss ({max_single_period_loss!r})"
            )
    except ValueError as exc:
        reasons.append(f"could not independently recompute VaR: {exc}")

    if reasons:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=reasons,
            failure_category=FailureCategory.DATA_QUALITY,
        )
    return Verdict(
        verdict_type=VerdictType.PASS,
        reasons=[
            "weights sum to 1, respect bounds, achieve target_return, and "
            "recomputed VaR is within max_single_period_loss"
        ],
    )
