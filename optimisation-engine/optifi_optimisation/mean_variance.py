"""
Mean-variance minimisation — OPTIMISATION_ENGINE_SPEC.md, Section 5.1,
plus a mandate loss-cap constraint layered on top of the same problem.
Section 5.2 (Sharpe-ratio maximisation), Section 5.3 (the efficient
frontier), the full Mandate constraint taxonomy (Section 6, beyond
generic per-asset weight bounds and the loss cap), and Section 8's
gate-checking remain separate, not-yet-implemented future work.

Uses cvxpy, since both problems here are convex quadratic programs
(minimise w^T Sigma w subject to linear and, for the loss-cap variant, one
convex quadratic constraint) — convexity depends on Sigma being positive
semi-definite, which quant-engine's `covariance_matrix` already
guarantees.
"""

from __future__ import annotations

import cvxpy as cp
import numpy as np
from scipy.stats import norm

from optifi_quant import parametric_var
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

# Section 9-style guard, applied here to solver output rather than a
# formula denominator: don't trust the solver's weights sum to 1 just
# because we asked for that constraint — verify it on the actual result.
_WEIGHTS_SUM_TOLERANCE = 1e-6

# Separate, deliberately distinct constant for the loss-cap re-verification
# guard (see minimize_variance_with_loss_cap below) — NOT the same
# tolerance as _WEIGHTS_SUM_TOLERANCE above, even though both currently
# happen to equal 1e-6. _WEIGHTS_SUM_TOLERANCE bounds a dimensionless
# quantity (weights summing to ~1.0); this one bounds a recomputed VaR
# against a Mandate loss cap that can be tens of thousands of pounds —
# a completely different numeric scale. Kept as its own named constant
# specifically so the two are never silently conflated or accidentally
# reused for each other's purpose. Chosen as a small absolute tolerance
# to absorb floating-point noise in the VaR recomputation (both
# portfolio_variance_value and the sqrt/z-score arithmetic feeding
# parametric_var), not because the Mandate's loss cap itself is expected
# to be precise to within 1e-6 of a pound.
_LOSS_CAP_REVERIFICATION_TOLERANCE = 1e-6


def _validate_and_build_matrices(
    expected_returns: dict[str, float],
    covariance: dict[str, dict[str, float]],
    fn_name: str,
) -> tuple[list[str], int, np.ndarray, np.ndarray]:
    """
    Shared input validation and matrix construction for both
    `minimize_variance` and `minimize_variance_with_loss_cap` — the same
    checks, applied identically to both, factored out rather than
    duplicated.
    """
    expected_return_assets = set(expected_returns.keys())
    covariance_assets = set(covariance.keys())
    if expected_return_assets != covariance_assets:
        raise ValueError(
            f"{fn_name}: the assets in `expected_returns` and "
            f"`covariance` must match exactly; expected_returns has "
            f"{sorted(expected_return_assets)}, covariance has "
            f"{sorted(covariance_assets)}."
        )
    for asset, row in covariance.items():
        row_assets = set(row.keys())
        if row_assets != covariance_assets:
            raise ValueError(
                f"{fn_name}: covariance matrix row '{asset}' does not "
                f"cover exactly the same asset set as the matrix's own "
                f"keys; expected {sorted(covariance_assets)}, got "
                f"{sorted(row_assets)}."
            )

    asset_order = sorted(expected_return_assets)
    n = len(asset_order)
    mu = np.array([expected_returns[a] for a in asset_order])
    sigma = np.array([[covariance[a][b] for b in asset_order] for a in asset_order])
    return asset_order, n, mu, sigma


def _source_id_links(
    covariance_source_id: str | None, expected_returns_source_id: str | None
) -> list[str]:
    """
    Gap 2 fix: neither `expected_returns` nor `covariance` is a UAP —
    both are raw dicts — so neither solver function has any way to record
    which upstream quant-engine UAP they came from unless the caller
    supplies that id explicitly. Both ids are optional; omitting either
    (or both) leaves the output exactly as before this fix — existing
    callers are unaffected.

    Populated into BOTH `dependencies` and `provenance_chain` (not just
    `dependencies` as the fix request literally named): verification-
    engine's `check_provenance_resolvable` reads `provenance_chain`
    specifically, not `dependencies` — populating only `dependencies`
    would leave that check exactly as vacuous as before, since it would
    still have an empty `provenance_chain` to look at. Both UAP fields
    describe the same relationship here (an upstream packet this result
    was derived from), so setting them identically is consistent with
    both fields' own definitions, not a workaround.
    """
    return [
        source_id
        for source_id in (covariance_source_id, expected_returns_source_id)
        if source_id is not None
    ]


def minimize_variance(
    expected_returns: dict[str, float],
    covariance: dict[str, dict[str, float]],
    target_return: float,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    covariance_source_id: str | None = None,
    expected_returns_source_id: str | None = None,
) -> UAP:
    """
    Minimise w^T Sigma w subject to:
      - w^T mu = target_return
      - sum(w) = 1
      - min_weight <= w_i <= max_weight for every asset

    `min_weight`/`max_weight` are generic per-asset bounds standing in for
    the real Mandate constraint set (OPTIMISATION_ENGINE_SPEC.md Section
    6), which this function does not implement.

    `covariance_source_id`/`expected_returns_source_id` are optional
    (Gap 2 fix, see `_source_id_links`) — when provided, both are
    recorded in the returned UAP's `dependencies` AND `provenance_chain`.
    Omitting either or both preserves this function's exact prior
    behaviour.
    """
    if min_weight > max_weight:
        raise ValueError(
            f"minimize_variance: min_weight ({min_weight!r}) must not "
            f"exceed max_weight ({max_weight!r})."
        )

    asset_order, n, mu, sigma = _validate_and_build_matrices(
        expected_returns, covariance, "minimize_variance"
    )

    w = cp.Variable(n)
    # assume_PSD=True: Sigma is already verified PSD by
    # quant-engine's covariance_matrix (QUANT_ENGINE_SPEC.md Section 9);
    # this avoids cvxpy re-deriving convexity from a matrix that may be
    # only PSD within our own floating-point tolerance.
    objective = cp.Minimize(cp.quad_form(w, sigma, assume_PSD=True))
    constraints = [
        cp.sum(w) == 1,
        w @ mu == target_return,
        w >= min_weight,
        w <= max_weight,
    ]
    problem = cp.Problem(objective, constraints)
    problem.solve()

    if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        raise ValueError(
            f"minimize_variance: no feasible portfolio exists for "
            f"target_return={target_return!r} given min_weight="
            f"{min_weight!r}, max_weight={max_weight!r}, and the provided "
            f"expected_returns (solver status: {problem.status!r}). This "
            "typically means target_return is outside the range of "
            "expected returns achievable under these weight bounds — "
            "adjust target_return or the bounds."
        )

    weights_array = np.asarray(w.value).flatten()
    weights = {asset: float(weights_array[i]) for i, asset in enumerate(asset_order)}

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > _WEIGHTS_SUM_TOLERANCE:
        raise ValueError(
            f"minimize_variance: solver reported status "
            f"{problem.status!r} but returned weights summing to "
            f"{weight_sum!r}, not within tolerance "
            f"({_WEIGHTS_SUM_TOLERANCE}) of 1.0 — solver output rejected "
            "rather than trusted (QUANT_ENGINE_SPEC.md Section 9's "
            "verify-don't-trust principle, applied here to a solver "
            "rather than a formula)."
        )

    portfolio_variance_value = float(weights_array @ sigma @ weights_array)

    return UAP(
        subject=f"minimum-variance portfolio: {', '.join(asset_order)}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "weights": weights,
            "portfolio_variance": portfolio_variance_value,
        },
        source=(
            "computed by minimising portfolio variance subject to a "
            "target return and generic weight bounds"
        ),
        producer="optimisation-engine / mean-variance minimisation, OPTIMISATION_ENGINE_SPEC.md Section 5.1",
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "generic per-asset weight bounds (min_weight/max_weight) were "
            "used, not the real Mandate constraint set "
            "(OPTIMISATION_ENGINE_SPEC.md Section 6)",
            "expected_returns and covariance are expressed over the same "
            "period and in consistent units",
        ],
        limitations=[
            "solves OPTIMISATION_ENGINE_SPEC.md Section 5.1 only — no "
            "Sharpe-ratio maximisation (Section 5.2), no efficient "
            "frontier (Section 5.3), and no gate-checking (Section 8)",
        ],
        dependencies=_source_id_links(covariance_source_id, expected_returns_source_id),
        provenance_chain=_source_id_links(covariance_source_id, expected_returns_source_id),
    )


def minimize_variance_with_loss_cap(
    expected_returns: dict[str, float],
    covariance: dict[str, dict[str, float]],
    target_return: float,
    portfolio_value: float,
    max_single_period_loss: float,
    confidence_level: float,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    covariance_source_id: str | None = None,
    expected_returns_source_id: str | None = None,
) -> UAP:
    """
    Solves the same problem as `minimize_variance` (Section 5.1) — same
    objective, same target-return/weight-sum/bound constraints — with one
    additional constraint enforcing the mandate's single-period loss cap
    directly in the solver, not as a downstream check on an already-solved
    candidate:

        Z_alpha * sqrt(w^T Sigma w) * portfolio_value <= max_single_period_loss

    `Z_alpha` is derived from `confidence_level` via `scipy.stats.norm.ppf`
    — the same approach quant-engine's `parametric_var` uses, not a
    separately reimplemented z-score lookup. Squaring both sides turns
    this into `w^T Sigma w <= (max_single_period_loss / (Z_alpha *
    portfolio_value))^2`, a convex quadratic constraint (quad_form of a
    PSD matrix bounded above by a constant) — DCP-compliant without
    needing an SOC formulation.

    Requires `confidence_level > 0.5` (a right-tail VaR threshold, e.g.
    0.95) — `parametric_var` itself tolerates confidence_level <= 0.5 (it
    floors VaR at 0.0 rather than reject it), but a non-positive Z_alpha
    would make the squared quadratic constraint above meaningless as an
    upper bound, so this function rejects that case explicitly rather
    than silently accepting a constraint that doesn't mean what it says.

    On infeasibility, distinguishes which constraint(s) are the cause:
    re-solves the *base* problem (without the loss-cap constraint) to
    check whether target_return/weight-bounds alone are already
    infeasible (same failure `minimize_variance` would report) versus
    feasible-but-conflicting-with-the-cap, in which case the error names
    the minimum achievable VaR at `target_return` and how it compares to
    `max_single_period_loss`.

    `covariance_source_id`/`expected_returns_source_id`: see
    `minimize_variance`'s docstring — same optional Gap 2 fix, same
    "omitted means unchanged" guarantee.
    """
    if not (0 < confidence_level < 1):
        raise ValueError(
            f"minimize_variance_with_loss_cap: confidence_level must be "
            f"strictly between 0 and 1, got {confidence_level!r}."
        )
    if confidence_level <= 0.5:
        raise ValueError(
            "minimize_variance_with_loss_cap: confidence_level must be "
            f"> 0.5 (a right-tail VaR threshold, e.g. 0.95); got "
            f"{confidence_level!r}, which would make the loss-cap "
            "constraint's direction meaningless once squared."
        )
    if portfolio_value <= 0:
        raise ValueError(
            f"minimize_variance_with_loss_cap: portfolio_value must be "
            f"positive, got {portfolio_value!r}."
        )
    if max_single_period_loss < 0:
        raise ValueError(
            "minimize_variance_with_loss_cap: max_single_period_loss "
            f"must be non-negative, got {max_single_period_loss!r}."
        )
    if min_weight > max_weight:
        raise ValueError(
            f"minimize_variance_with_loss_cap: min_weight ({min_weight!r}) "
            f"must not exceed max_weight ({max_weight!r})."
        )

    asset_order, n, mu, sigma = _validate_and_build_matrices(
        expected_returns, covariance, "minimize_variance_with_loss_cap"
    )

    z_alpha = float(norm.ppf(confidence_level))

    w = cp.Variable(n)
    objective = cp.Minimize(cp.quad_form(w, sigma, assume_PSD=True))
    base_constraints = [
        cp.sum(w) == 1,
        w @ mu == target_return,
        w >= min_weight,
        w <= max_weight,
    ]
    loss_cap_bound = (max_single_period_loss / (z_alpha * portfolio_value)) ** 2
    loss_cap_constraint = cp.quad_form(w, sigma, assume_PSD=True) <= loss_cap_bound

    problem = cp.Problem(objective, [*base_constraints, loss_cap_constraint])
    problem.solve()

    if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        # Diagnose which constraint(s) caused infeasibility rather than
        # reporting a single undifferentiated failure.
        base_problem = cp.Problem(objective, base_constraints)
        base_problem.solve()

        if base_problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            raise ValueError(
                f"minimize_variance_with_loss_cap: no feasible portfolio "
                f"exists for target_return={target_return!r} given "
                f"min_weight={min_weight!r}, max_weight={max_weight!r}, "
                f"and the provided expected_returns — infeasible before "
                f"the loss cap is even considered (base solver status: "
                f"{base_problem.status!r}). Adjust target_return or the "
                "weight bounds."
            )

        # base_problem shares the same `w` Variable object as `problem`,
        # so w.value after base_problem.solve() reflects the base-only
        # solution directly.
        base_weights_array = np.asarray(w.value).flatten()
        min_achievable_variance = float(base_weights_array @ sigma @ base_weights_array)
        min_achievable_var = parametric_var(
            portfolio_value=portfolio_value,
            portfolio_std_dev=min_achievable_variance**0.5,
            confidence_level=confidence_level,
        ).result

        raise ValueError(
            f"minimize_variance_with_loss_cap: target_return="
            f"{target_return!r} is achievable within the weight bounds "
            f"(base constraints are feasible), but every portfolio "
            f"achieving it violates the loss cap. The minimum achievable "
            f"VaR at this target_return is {min_achievable_var!r}, which "
            f"exceeds max_single_period_loss={max_single_period_loss!r} "
            f"at {confidence_level:.0%} confidence. Loosen the cap, "
            "lower target_return, or widen the weight bounds."
        )

    weights_array = np.asarray(w.value).flatten()
    weights = {asset: float(weights_array[i]) for i, asset in enumerate(asset_order)}

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > _WEIGHTS_SUM_TOLERANCE:
        raise ValueError(
            f"minimize_variance_with_loss_cap: solver reported status "
            f"{problem.status!r} but returned weights summing to "
            f"{weight_sum!r}, not within tolerance "
            f"({_WEIGHTS_SUM_TOLERANCE}) of 1.0 — solver output rejected "
            "rather than trusted."
        )

    portfolio_variance_value = float(weights_array @ sigma @ weights_array)
    value_at_risk = parametric_var(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_variance_value**0.5,
        confidence_level=confidence_level,
    ).result

    # Solver-output guard, mirroring the weights-sum-to-one check above:
    # the loss-cap constraint was enforced during solving, but its
    # satisfaction is re-verified independently from the solved weights
    # rather than assumed from the solver's reported status alone.
    if value_at_risk > max_single_period_loss + _LOSS_CAP_REVERIFICATION_TOLERANCE:
        raise ValueError(
            f"minimize_variance_with_loss_cap: solver reported status "
            f"{problem.status!r} but the recomputed VaR "
            f"({value_at_risk!r}) exceeds max_single_period_loss "
            f"({max_single_period_loss!r}) — solver output rejected "
            "rather than trusted."
        )

    return UAP(
        subject=f"minimum-variance portfolio with loss cap: {', '.join(asset_order)}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "weights": weights,
            "portfolio_variance": portfolio_variance_value,
            "value_at_risk": value_at_risk,
        },
        source=(
            "computed by minimising portfolio variance subject to a "
            "target return, generic weight bounds, and a mandate "
            "single-period loss cap enforced as a solver constraint"
        ),
        producer=(
            "optimisation-engine / mean-variance minimisation with loss "
            "cap, OPTIMISATION_ENGINE_SPEC.md Section 5.1 plus a mandate "
            "loss-cap constraint"
        ),
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "generic per-asset weight bounds (min_weight/max_weight) were "
            "used, not the real Mandate constraint set "
            "(OPTIMISATION_ENGINE_SPEC.md Section 6)",
            "expected_returns and covariance are expressed over the same "
            "period and in consistent units",
            "portfolio returns are normally distributed, consistent with "
            "quant-engine's parametric_var, which this function reuses "
            "for the reported value_at_risk",
        ],
        limitations=[
            "solves OPTIMISATION_ENGINE_SPEC.md Section 5.1 plus a single "
            "loss-cap constraint only — no Sharpe-ratio maximisation "
            "(Section 5.2), no efficient frontier (Section 5.3), no "
            "gate-checking (Section 8), and no other Mandate constraint "
            "from Section 6",
            "the loss cap is enforced via parametric (normal-distribution) "
            "VaR, inheriting parametric_var's known understatement of "
            "tail risk for fatter-tailed real return distributions",
        ],
        dependencies=_source_id_links(covariance_source_id, expected_returns_source_id),
        provenance_chain=_source_id_links(covariance_source_id, expected_returns_source_id),
    )
