"""
Mean-variance minimisation — OPTIMISATION_ENGINE_SPEC.md, Section 5.1
only. Section 5.2 (Sharpe-ratio maximisation), Section 5.3 (the efficient
frontier), the full Mandate constraint taxonomy (Section 6, beyond generic
per-asset weight bounds), and Section 8's gate-checking are all separate,
not-yet-implemented future work.

Uses cvxpy, since Section 5.1's problem is a convex quadratic program
(minimise w^T Sigma w subject to linear constraints) — convexity here
depends on Sigma being positive semi-definite, which quant-engine's
`covariance_matrix` already guarantees.
"""

from __future__ import annotations

import cvxpy as cp
import numpy as np

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

# Section 9-style guard, applied here to solver output rather than a
# formula denominator: don't trust the solver's weights sum to 1 just
# because we asked for that constraint — verify it on the actual result.
_WEIGHTS_SUM_TOLERANCE = 1e-6


def minimize_variance(
    expected_returns: dict[str, float],
    covariance: dict[str, dict[str, float]],
    target_return: float,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> UAP:
    """
    Minimise w^T Sigma w subject to:
      - w^T mu = target_return
      - sum(w) = 1
      - min_weight <= w_i <= max_weight for every asset

    `min_weight`/`max_weight` are generic per-asset bounds standing in for
    the real Mandate constraint set (OPTIMISATION_ENGINE_SPEC.md Section
    6), which this function does not implement.
    """
    if min_weight > max_weight:
        raise ValueError(
            f"minimize_variance: min_weight ({min_weight!r}) must not "
            f"exceed max_weight ({max_weight!r})."
        )

    expected_return_assets = set(expected_returns.keys())
    covariance_assets = set(covariance.keys())
    if expected_return_assets != covariance_assets:
        raise ValueError(
            "minimize_variance: the assets in `expected_returns` and "
            f"`covariance` must match exactly; expected_returns has "
            f"{sorted(expected_return_assets)}, covariance has "
            f"{sorted(covariance_assets)}."
        )
    for asset, row in covariance.items():
        row_assets = set(row.keys())
        if row_assets != covariance_assets:
            raise ValueError(
                f"minimize_variance: covariance matrix row '{asset}' does "
                f"not cover exactly the same asset set as the matrix's "
                f"own keys; expected {sorted(covariance_assets)}, got "
                f"{sorted(row_assets)}."
            )

    asset_order = sorted(expected_return_assets)
    n = len(asset_order)
    mu = np.array([expected_returns[a] for a in asset_order])
    sigma = np.array([[covariance[a][b] for b in asset_order] for a in asset_order])

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
        dependencies=[],
    )
