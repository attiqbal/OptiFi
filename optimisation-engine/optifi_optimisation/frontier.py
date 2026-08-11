"""
The efficient frontier (OPTIMISATION_ENGINE_SPEC.md, Section 5.3) and the
maximum-Sharpe-ratio tangency portfolio (Section 5.2).

Both functions in this module make the same DESIGNED decision, filling a
genuine spec gap — see `_LOSS_CAP_RATIONALE` below (the same reasoning
is restated in both functions' own docstrings and in their output UAPs'
`assumptions`) — and both leave the risk-free rate `R_f` as a
caller-supplied parameter, since QUANT_ENGINE_SPEC.md and
OPTIMISATION_ENGINE_SPEC.md name no data source for it anywhere (the same
treatment already given to Cash efficiency's
`best_available_comparable_yield` in `quant-engine`).
"""

from __future__ import annotations

import cvxpy as cp
import numpy as np
from scipy.stats import norm

from optifi_quant import parametric_var, sharpe_ratio
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .mean_variance import (
    _LOSS_CAP_REVERIFICATION_TOLERANCE,
    _validate_and_build_matrices,
    _WEIGHTS_SUM_TOLERANCE,
    minimize_variance_with_loss_cap,
)

# DESIGNED, not a literal transcription of OPTIMISATION_ENGINE_SPEC.md:
# Section 5.3 technically defines the frontier as "the set of portfolios
# solving Section 5.1" (the UNCAPPED problem) across varying R_target,
# and Section 5.2's max-Sharpe objective is likewise stated only
# "subject to the same constraint set" without explicitly naming the
# loss cap (Section 5.1a). Both functions in this module use
# `minimize_variance_with_loss_cap` (Section 5.1a) instead of the
# uncapped `minimize_variance` (Section 5.1) anyway. Reasoning: a
# "maximum achievable" benchmark that ignores the user's own stated loss
# tolerance isn't actually achievable for that user — it would make
# Investment Efficiency (QUANT_ENGINE_SPEC.md Section 7) structurally
# impossible to score well on for anyone with a real
# max_single_period_loss constraint, since their real candidates are
# always loss-capped but the benchmark they're compared against would
# not be. This is an engineering decision extending Section 5.3/5.2's
# literal scope to Section 5.1a, not something either section states.
_LOSS_CAP_RATIONALE = (
    "DESIGNED: uses the loss-capped solver (Section 5.1a), not the "
    "uncapped one Section 5.3/5.2 literally reference (Section 5.1) -- "
    "a 'maximum achievable' benchmark that ignores the user's own loss "
    "cap isn't actually achievable for that user, which would make "
    "Investment Efficiency structurally impossible to score well on for "
    "anyone with a real max_single_period_loss constraint."
)

# DESIGNED: OPTIMISATION_ENGINE_SPEC.md gives no target-return sweep
# range or granularity anywhere. 21 points was chosen to give a
# reasonably fine-grained trace of the frontier's shape (roughly one
# point per 5% of the return range) without requiring an excessive
# number of repeated QP solves -- an arbitrary, documented placeholder,
# not a spec-derived value.
_FRONTIER_SWEEP_POINT_COUNT = 21

# Solver-output guard: kappa (the tangency-portfolio reformulation's
# scaling variable, see `maximum_sharpe_ratio`) must be strictly
# positive by construction (kappa = 1 / (achieved excess return) at the
# optimum) -- a solver value at or below this epsilon indicates the
# reformulation's own precondition (a feasible portfolio exists with
# positive expected excess return over R_f) has broken down, not a
# result to trust.
_KAPPA_EPSILON = 1e-8


def _validate_loss_cap_parameters(
    confidence_level: float, portfolio_value: float, max_single_period_loss: float, fn_name: str
) -> None:
    """
    Shared guards, identical to the ones `minimize_variance_with_loss_cap`
    applies to the same three parameters -- factored out here since three
    functions in this package now need them (the base loss-cap solver,
    plus this module's two), rather than tripling the same four checks.
    """
    if not (0 < confidence_level < 1):
        raise ValueError(
            f"{fn_name}: confidence_level must be strictly between 0 and "
            f"1, got {confidence_level!r}."
        )
    if confidence_level <= 0.5:
        raise ValueError(
            f"{fn_name}: confidence_level must be > 0.5 (a right-tail VaR "
            f"threshold, e.g. 0.95); got {confidence_level!r}, which "
            "would make the loss-cap constraint's direction meaningless "
            "once squared."
        )
    if portfolio_value <= 0:
        raise ValueError(
            f"{fn_name}: portfolio_value must be positive, got {portfolio_value!r}."
        )
    if max_single_period_loss < 0:
        raise ValueError(
            f"{fn_name}: max_single_period_loss must be non-negative, "
            f"got {max_single_period_loss!r}."
        )


def _global_minimum_variance_return(
    mu: np.ndarray, sigma: np.ndarray, n: int, min_weight: float, max_weight: float, fn_name: str
) -> float:
    """
    The achieved return of the GLOBAL minimum-variance portfolio -- sum(w)
    = 1 and the weight bounds, but deliberately no target-return equality
    constraint at all. This is DESIGNED as the frontier sweep's lower
    bound (OPTIMISATION_ENGINE_SPEC.md gives no sweep range anywhere):
    no feasible portfolio can achieve a target_return below this value at
    a lower-or-equal variance than the global minimum itself allows, so
    sweeping below it would only ever hit points strictly dominated by
    this one -- not genuinely new frontier shape.
    """
    w = cp.Variable(n)
    objective = cp.Minimize(cp.quad_form(w, sigma, assume_PSD=True))
    constraints = [cp.sum(w) == 1, w >= min_weight, w <= max_weight]
    problem = cp.Problem(objective, constraints)
    problem.solve()

    if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        raise ValueError(
            f"{fn_name}: could not determine the sweep range's lower "
            f"bound -- the global minimum-variance portfolio (sum(w)=1, "
            f"min_weight={min_weight!r}, max_weight={max_weight!r}, no "
            f"target-return constraint) is itself infeasible (solver "
            f"status: {problem.status!r})."
        )

    weights_array = np.asarray(w.value).flatten()
    return float(weights_array @ mu)


def efficient_frontier(
    expected_returns: dict[str, float],
    covariance: dict[str, dict[str, float]],
    portfolio_value: float,
    max_single_period_loss: float,
    confidence_level: float,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    covariance_source_id: str | None = None,
    expected_returns_source_id: str | None = None,
) -> UAP:
    """
    The efficient frontier (OPTIMISATION_ENGINE_SPEC.md Section 5.3):
    "the set of portfolios solving Section 5.1 across varying R_target —
    tracing achievable risk/return combinations."

    Three DESIGNED decisions fill gaps Section 5.3 leaves genuinely open:

    1. Loss cap -- DESIGNED: uses the loss-capped solver (Section 5.1a),
       not the uncapped one Section 5.3 literally references (Section
       5.1). A "maximum achievable" benchmark that ignores the user's
       own loss cap isn't actually achievable for that user, which would
       make Investment Efficiency structurally impossible to score well
       on for anyone with a real max_single_period_loss constraint.

    2. Sweep range: computed, not hardcoded. The lower bound is the
       global minimum-variance portfolio's own achieved return (see
       `_global_minimum_variance_return` -- nothing below it is a
       genuinely new, non-dominated frontier point). The upper bound is
       the highest expected return among the assets provided ("anything
       beyond that is guaranteed infeasible or dominated" per this
       task's own instruction -- no target_return above the single best
       asset's own expected return can ever be achieved by ANY
       combination of these assets, since a weighted average can never
       exceed its own maximum input). `_FRONTIER_SWEEP_POINT_COUNT`
       evenly spaced points are swept across that range.

    3. Infeasibility handling: `minimize_variance_with_loss_cap` raises
       `ValueError` for a target_return that turns out to be infeasible
       (either the base weight-bound problem, or the loss cap once
       layered on). Rather than letting the whole frontier computation
       fail because ONE swept point is infeasible, each point is solved
       independently; infeasible points are skipped, not forced into the
       frontier or silently dropped -- every skip is recorded, with its
       exact target_return and the reason, in the returned UAP's
       `limitations` field.
    """
    _validate_loss_cap_parameters(
        confidence_level, portfolio_value, max_single_period_loss, "efficient_frontier"
    )
    if min_weight > max_weight:
        raise ValueError(
            f"efficient_frontier: min_weight ({min_weight!r}) must not "
            f"exceed max_weight ({max_weight!r})."
        )

    asset_order, n, mu, sigma = _validate_and_build_matrices(
        expected_returns, covariance, "efficient_frontier"
    )

    lower_bound = _global_minimum_variance_return(mu, sigma, n, min_weight, max_weight, "efficient_frontier")
    upper_bound = max(expected_returns.values())

    if lower_bound > upper_bound:
        raise ValueError(
            f"efficient_frontier: computed sweep range is empty -- the "
            f"global minimum-variance portfolio's own achieved return "
            f"({lower_bound!r}) exceeds the highest available expected "
            f"return ({upper_bound!r}). This should not occur for a "
            "well-formed expected_returns/covariance pair."
        )

    target_returns = np.linspace(lower_bound, upper_bound, _FRONTIER_SWEEP_POINT_COUNT)

    frontier_points: list[dict] = []
    skipped: list[dict] = []
    for target_return in target_returns:
        target_return = float(target_return)
        try:
            point_uap = minimize_variance_with_loss_cap(
                expected_returns,
                covariance,
                target_return,
                portfolio_value=portfolio_value,
                max_single_period_loss=max_single_period_loss,
                confidence_level=confidence_level,
                min_weight=min_weight,
                max_weight=max_weight,
            )
        except ValueError as exc:
            skipped.append({"target_return": target_return, "reason": str(exc)})
            continue

        frontier_points.append(
            {
                "target_return": target_return,
                "weights": point_uap.result["weights"],
                "portfolio_variance": point_uap.result["portfolio_variance"],
                "value_at_risk": point_uap.result["value_at_risk"],
            }
        )

    if not frontier_points:
        raise ValueError(
            "efficient_frontier: every swept target_return was infeasible "
            f"-- {len(skipped)} point(s) skipped, none produced a "
            "feasible frontier point. The loss cap or weight bounds may "
            "be too tight for this asset set."
        )

    skipped_summary = [
        f"target_return={s['target_return']!r} skipped: {s['reason']}" for s in skipped
    ]

    return UAP(
        subject=f"efficient frontier: {', '.join(asset_order)}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "frontier_points": frontier_points,
            "target_return_range": {"min": lower_bound, "max": upper_bound},
            "swept_point_count": _FRONTIER_SWEEP_POINT_COUNT,
            "feasible_point_count": len(frontier_points),
            "skipped_point_count": len(skipped),
        },
        source=(
            "computed by solving minimize_variance_with_loss_cap across "
            f"{_FRONTIER_SWEEP_POINT_COUNT} target_return values swept "
            "from the global minimum-variance portfolio's own achieved "
            "return to the highest available expected return"
        ),
        producer=(
            "optimisation-engine / efficient frontier (DESIGNED sweep "
            "range/granularity, DESIGNED loss-cap extension; see "
            "docstring), OPTIMISATION_ENGINE_SPEC.md Section 5.3"
        ),
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "generic per-asset weight bounds (min_weight/max_weight) were "
            "used, not the real Mandate constraint set "
            "(OPTIMISATION_ENGINE_SPEC.md Section 6)",
            _LOSS_CAP_RATIONALE,
            f"{_FRONTIER_SWEEP_POINT_COUNT} evenly spaced sweep points is "
            "an explicit, undocumented-in-spec calibration placeholder, "
            "not a QUANT_ENGINE_SPEC.md/OPTIMISATION_ENGINE_SPEC.md value",
        ],
        limitations=[
            "solves OPTIMISATION_ENGINE_SPEC.md Section 5.1 plus the loss "
            "cap only -- no other Mandate constraint from Section 6, and "
            "no gate-checking (Section 8)",
            f"{len(skipped)} of {_FRONTIER_SWEEP_POINT_COUNT} swept "
            "target_return values were infeasible and skipped (not "
            "included in frontier_points): " + ("; ".join(skipped_summary) if skipped_summary else "none"),
        ],
        dependencies=[
            source_id
            for source_id in (covariance_source_id, expected_returns_source_id)
            if source_id is not None
        ],
        provenance_chain=[
            source_id
            for source_id in (covariance_source_id, expected_returns_source_id)
            if source_id is not None
        ],
    )


def maximum_sharpe_ratio(
    expected_returns: dict[str, float],
    covariance: dict[str, dict[str, float]],
    risk_free_rate: float,
    portfolio_value: float,
    max_single_period_loss: float,
    confidence_level: float,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    covariance_source_id: str | None = None,
    expected_returns_source_id: str | None = None,
) -> UAP:
    """
    The maximum-Sharpe-ratio tangency portfolio (OPTIMISATION_ENGINE_SPEC.md
    Section 5.2): maximise `(w^T mu - R_f) / sqrt(w^T Sigma w)` subject to
    sum(w)=1, the weight bounds, and the loss cap.

    Loss cap -- DESIGNED: Section 5.2 states only "subject to the same
    constraint set" without naming the loss cap (Section 5.1a)
    explicitly. This function includes it anyway, for the same reason
    `efficient_frontier` does: a "maximum achievable" benchmark that
    ignores the user's own loss cap isn't actually achievable for that
    user, which would make Investment Efficiency structurally
    impossible to score well on for anyone with a real
    max_single_period_loss constraint.

    `risk_free_rate` (R_f) has no data source specified anywhere in
    QUANT_ENGINE_SPEC.md or OPTIMISATION_ENGINE_SPEC.md -- treated here
    as an assumed input parameter the caller supplies, the same
    treatment `quant-engine`'s Cash efficiency sub-score already gives
    `best_available_comparable_yield` pending the Phase 3 vendor
    decision.

    Raw Sharpe-ratio maximisation is not directly convex, so `cvxpy`
    cannot solve it as stated. This uses the standard Markowitz
    tangency-portfolio reformulation instead of an approximation:
    substituting `kappa = 1 / (w^T mu - R_f)` and `y = kappa * w`
    (equivalently, per this task's own phrasing, `y = w / (w^T mu -
    R_f)`) turns the problem into the convex QP

        minimise  y^T Sigma y
        subject to  y^T mu - R_f * kappa = 1
                    sum(y) = kappa
                    min_weight * kappa <= y_i <= max_weight * kappa
                    kappa >= _KAPPA_EPSILON   (kappa must be strictly
                                          positive by construction; a
                                          small positive floor stands in
                                          for that strict inequality,
                                          which no solver can express
                                          directly)

    minimising y^T Sigma y at this fixed normalisation is exactly
    equivalent to maximising the original Sharpe ratio (see this
    module's own derivation notes below) -- not an approximation of it.
    The loss cap is expressed in (y, kappa)-space as the second-order
    cone constraint `||Sigma^(1/2) y||_2 <= L * kappa`, where `L =
    max_single_period_loss / (Z_alpha * portfolio_value)` -- the same L
    `minimize_variance_with_loss_cap` squares directly in w-space; taking
    the square root here instead keeps the constraint DCP-compliant
    (comparing a convex norm against an AFFINE right-hand side, rather
    than comparing two convex quadratics against each other, which cvxpy
    cannot accept).

    After solving, weights are recovered via `w = y / sum(y)` (per this
    task's own instruction), and the achieved Sharpe ratio is recomputed
    independently from those final weights via `quant-engine`'s own
    `sharpe_ratio` function -- reused rather than reimplemented, and
    recomputed from the solved weights rather than trusted from the QP's
    internal (y, kappa) state, consistent with this package's existing
    verify-don't-trust convention.

    Derivation note: with `kappa = 1/(w^T mu - R_f)` and `y = kappa * w`,
    `y^T mu - R_f * kappa = kappa * (w^T mu - R_f) = 1` (matches the
    normalisation constraint above); `sum(y) = kappa * sum(w) = kappa`
    (matches the sum constraint); and `w^T Sigma w = y^T Sigma y /
    kappa^2`, so `(w^T mu - R_f) / sqrt(w^T Sigma w) = (1/kappa) /
    (sqrt(y^T Sigma y)/kappa) = 1 / sqrt(y^T Sigma y)` -- maximising the
    left-hand side is therefore exactly equivalent to minimising `y^T
    Sigma y`.
    """
    _validate_loss_cap_parameters(
        confidence_level, portfolio_value, max_single_period_loss, "maximum_sharpe_ratio"
    )
    if min_weight > max_weight:
        raise ValueError(
            f"maximum_sharpe_ratio: min_weight ({min_weight!r}) must not "
            f"exceed max_weight ({max_weight!r})."
        )

    asset_order, n, mu, sigma = _validate_and_build_matrices(
        expected_returns, covariance, "maximum_sharpe_ratio"
    )

    z_alpha = float(norm.ppf(confidence_level))
    loss_cap_l = max_single_period_loss / (z_alpha * portfolio_value)

    # Symmetric PSD square root of Sigma via eigendecomposition (Sigma is
    # already guaranteed PSD by quant-engine's covariance_matrix,
    # QUANT_ENGINE_SPEC.md Section 9) -- eigenvalues are clipped at 0 to
    # absorb floating-point noise that could otherwise produce a tiny
    # negative eigenvalue and an invalid (complex) square root.
    eigvals, eigvecs = np.linalg.eigh(sigma)
    eigvals_clipped = np.clip(eigvals, 0.0, None)
    sigma_sqrt = eigvecs @ np.diag(np.sqrt(eigvals_clipped)) @ eigvecs.T

    y = cp.Variable(n)
    kappa = cp.Variable()
    objective = cp.Minimize(cp.quad_form(y, sigma, assume_PSD=True))
    base_constraints = [
        y @ mu - risk_free_rate * kappa == 1,
        cp.sum(y) == kappa,
        y >= min_weight * kappa,
        y <= max_weight * kappa,
        kappa >= _KAPPA_EPSILON,
    ]
    loss_cap_constraint = cp.norm(sigma_sqrt @ y, 2) <= loss_cap_l * kappa

    problem = cp.Problem(objective, [*base_constraints, loss_cap_constraint])
    problem.solve()

    if problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        base_problem = cp.Problem(objective, base_constraints)
        base_problem.solve()

        if base_problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            raise ValueError(
                "maximum_sharpe_ratio: no feasible tangency portfolio "
                f"exists given min_weight={min_weight!r}, "
                f"max_weight={max_weight!r}, risk_free_rate="
                f"{risk_free_rate!r}, and the provided expected_returns "
                "-- infeasible before the loss cap is even considered "
                f"(base solver status: {base_problem.status!r}). This "
                "can also occur if no feasible portfolio has positive "
                "expected excess return over risk_free_rate, which this "
                "reformulation's kappa substitution assumes."
            )

        raise ValueError(
            "maximum_sharpe_ratio: the unconstrained tangency portfolio "
            "is achievable within the weight bounds, but every portfolio "
            "achieving it violates the loss cap (loss-cap-constrained "
            f"solver status: {problem.status!r}). Loosen the cap or "
            "widen the weight bounds."
        )

    y_array = np.asarray(y.value).flatten()
    y_sum = float(np.sum(y_array))
    if abs(y_sum) < _KAPPA_EPSILON:
        raise ValueError(
            "maximum_sharpe_ratio: solver reported status "
            f"{problem.status!r} but sum(y) ({y_sum!r}) is at or below "
            f"the epsilon threshold ({_KAPPA_EPSILON}) -- cannot recover "
            "portfolio weights via w = y / sum(y)."
        )

    weights_array = y_array / y_sum
    weights = {asset: float(weights_array[i]) for i, asset in enumerate(asset_order)}

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > _WEIGHTS_SUM_TOLERANCE:
        raise ValueError(
            f"maximum_sharpe_ratio: solver reported status "
            f"{problem.status!r} but recovered weights summing to "
            f"{weight_sum!r}, not within tolerance "
            f"({_WEIGHTS_SUM_TOLERANCE}) of 1.0 -- solver output rejected "
            "rather than trusted."
        )

    portfolio_return = float(weights_array @ mu)
    portfolio_variance_value = float(weights_array @ sigma @ weights_array)
    portfolio_std_dev = portfolio_variance_value**0.5

    achieved_sharpe_uap = sharpe_ratio(
        portfolio_return=portfolio_return,
        risk_free_rate=risk_free_rate,
        portfolio_std_dev=portfolio_std_dev,
    )

    value_at_risk = parametric_var(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
    ).result

    if value_at_risk > max_single_period_loss + _LOSS_CAP_REVERIFICATION_TOLERANCE:
        raise ValueError(
            f"maximum_sharpe_ratio: solver reported status "
            f"{problem.status!r} but the recomputed VaR "
            f"({value_at_risk!r}) exceeds max_single_period_loss "
            f"({max_single_period_loss!r}) -- solver output rejected "
            "rather than trusted."
        )

    return UAP(
        subject=f"maximum Sharpe ratio (tangency) portfolio: {', '.join(asset_order)}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "weights": weights,
            "sharpe_ratio": achieved_sharpe_uap.result,
            "portfolio_return": portfolio_return,
            "portfolio_variance": portfolio_variance_value,
            "value_at_risk": value_at_risk,
        },
        source=(
            "computed via the Markowitz tangency-portfolio convex "
            "reformulation (kappa/y substitution), subject to weight "
            "bounds, a mandate single-period loss cap, and the provided "
            "risk_free_rate"
        ),
        producer=(
            "optimisation-engine / maximum Sharpe ratio (tangency "
            "portfolio) (DESIGNED loss-cap extension; see docstring), "
            "OPTIMISATION_ENGINE_SPEC.md Section 5.2"
        ),
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "generic per-asset weight bounds (min_weight/max_weight) were "
            "used, not the real Mandate constraint set "
            "(OPTIMISATION_ENGINE_SPEC.md Section 6)",
            "risk_free_rate is supplied by the caller; this function "
            "does not source or validate it against any real "
            "market-data feed -- QUANT_ENGINE_SPEC.md/"
            "OPTIMISATION_ENGINE_SPEC.md name no data source for it",
            "the kappa/y reformulation assumes a feasible portfolio "
            "exists with positive expected excess return over "
            "risk_free_rate; if none does, this function reports "
            "infeasibility rather than a meaningful (negative-excess) "
            "tangency portfolio",
            _LOSS_CAP_RATIONALE,
            "portfolio returns are normally distributed, consistent with "
            "quant-engine's parametric_var, which this function reuses "
            "for the reported value_at_risk",
        ],
        limitations=[
            "solves OPTIMISATION_ENGINE_SPEC.md Section 5.2 plus the loss "
            "cap only -- no other Mandate constraint from Section 6, and "
            "no gate-checking (Section 8)",
            "the loss cap is enforced via parametric (normal-distribution) "
            "VaR, inheriting parametric_var's known understatement of "
            "tail risk for fatter-tailed real return distributions",
        ],
        dependencies=[
            source_id
            for source_id in (covariance_source_id, expected_returns_source_id)
            if source_id is not None
        ],
        provenance_chain=[
            source_id
            for source_id in (covariance_source_id, expected_returns_source_id)
            if source_id is not None
        ],
    )
