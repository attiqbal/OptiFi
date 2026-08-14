"""
Asset-response sensitivities — PHASE E4 brief, Part 3 ("Empirical Asset
Sensitivity") and Part 1's separation of concepts: a sensitivity answers
"how might this asset react under this state?" — genuinely distinct from
a forecast ("what appears likely?") or a scenario ("what if this state
occurs?"). Neither function here produces either of those.

Two functions, DELIBERATELY kept structurally separate per the brief's
own instruction ("keep deterministic relationships separate from
statistical relationships"):

- `estimate_factor_sensitivity` — a STATISTICAL relationship: an OLS beta
  estimated from historical factor/asset return series, reusing
  `covariance_matrix` exactly the way `hedging.py`'s
  `minimum_variance_hedge_ratio` already does (`beta = Cov(factor, asset)
  / Var(factor)` is structurally the same formula as the hedge ratio and
  as QUANT_ENGINE_SPEC.md Section 5.3's Beta — one more application of
  existing machinery, not a new statistical method).
- `duration_price_sensitivity` — a DETERMINISTIC relationship: the
  standard closed-form bond-duration approximation
  (`ΔPrice/Price ≈ -ModifiedDuration × Δyield`), computed directly from a
  known duration figure, no historical sample or regression involved.

Both return a UAP whose `result` shares one common shape —
`{"sensitivity": float, "method": str, ...}` — so `simulation-engine`'s
propagation logic can treat "how much does this factor move this asset"
uniformly regardless of which kind of relationship supplied it, while the
`method` field keeps the provenance honest (a consumer, or a human, can
always tell which kind of claim they're looking at).

Note on scope: this module is NOT QUANT_ENGINE_SPEC.md Section 5.4's
"factor exposure" (style-factor tilts — value, size, momentum, quality,
low-volatility). That remains a separate, still-unresolved choice
(Section 11, item 4). What's implemented here is sensitivity to a named
MACRO/MARKET DRIVER (a yield, a rate, an FX pair, inflation) for the
purpose of scenario transmission (PHASE E4) — a different axis of
"factor" than the equity style-factor model. Conflating the two would
misrepresent this phase as having resolved a question it did not touch.
"""

from __future__ import annotations

from optifi_shared import ConfidenceLevel, InformationClass, InsufficientDataFailure, UAP, ValidationStatus

from .covariance import covariance_matrix

# Below this many paired observations, a regression-based sensitivity is
# not a meaningful statistical estimate (too few degrees of freedom to
# trust) — distinct from, and stricter than, covariance_matrix's own
# floor of 2 observations, which only guards against a mathematically
# undefined computation, not a STATISTICALLY MEANINGFUL one. A
# documented calibration choice (roughly "a year of monthly data"), not
# a value fixed by any spec document.
DEFAULT_MIN_OBSERVATIONS = 12
# Below this many observations, even an accepted estimate (>= the floor
# above) is downgraded to LOW confidence rather than MODERATE — a
# genuinely small sample is a weaker basis for trust even once it clears
# the hard minimum.
_ROBUST_OBSERVATIONS_THRESHOLD = 36

_STD_DEV_EPSILON = 1e-12


def estimate_factor_sensitivity(
    factor_id: str,
    asset_id: str,
    factor_returns: list[float],
    asset_returns: list[float],
    horizon: str,
    regime: str | None = None,
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
    disagreement_set_ref: str | None = None,
) -> UAP:
    """
    Statistical sensitivity of `asset_id` to `factor_id`:
    `beta = Cov(factor, asset) / Var(factor)`, estimated from paired
    historical return series — "estimate historical sensitivities rather
    than manually choosing them" (Part 3).

    `horizon` (e.g. "1-month") states the return interval the series is
    sampled at — required, not optional, because a sensitivity estimated
    from monthly data does not necessarily apply to a scenario framed
    over a different horizon (`simulation-engine`'s propagation logic
    checks this explicitly — Testing Requirement "wrong-horizon
    sensitivity").

    `regime`, if given, tags which market/economic regime this specific
    estimate was computed FROM (the caller is responsible for having
    already filtered `factor_returns`/`asset_returns` to that regime's
    historical window — this function does not itself classify regimes;
    see `SensitivityRegistry`'s own module docstring for why regime
    detection is left as an open research question, not silently
    invented here).

    Raises `InsufficientDataFailure` below `min_observations` — Testing
    Requirement "sensitivity estimated from insufficient history."
    """
    if min_observations < 3:
        raise ValueError(
            f"estimate_factor_sensitivity: min_observations ({min_observations!r}) "
            "must be at least 3 — the standard-error computation below needs "
            "n > 2 degrees of freedom (n-2 denominator)."
        )
    n = len(factor_returns)
    if n < min_observations or len(asset_returns) < min_observations:
        raise InsufficientDataFailure(
            f"estimate_factor_sensitivity: {min(n, len(asset_returns))} paired "
            f"observations available for {factor_id!r} -> {asset_id!r}, need at "
            f"least {min_observations} for a statistically meaningful estimate."
        )
    if len(factor_returns) != len(asset_returns):
        raise ValueError(
            f"estimate_factor_sensitivity: factor_returns ({len(factor_returns)}) "
            f"and asset_returns ({len(asset_returns)}) must be the same length "
            "(paired, aligned observations)."
        )

    cov_uap = covariance_matrix({factor_id: factor_returns, asset_id: asset_returns})
    matrix = cov_uap.result
    var_factor = matrix[factor_id][factor_id]
    var_asset = matrix[asset_id][asset_id]
    cov_factor_asset = matrix[factor_id][asset_id]

    if var_factor**0.5 < _STD_DEV_EPSILON:
        raise ValueError(
            f"estimate_factor_sensitivity: {factor_id!r} has zero or "
            f"near-zero variance ({var_factor!r}); sensitivity "
            "(Cov/Var(factor)) is undefined for a constant factor series."
        )

    beta = cov_factor_asset / var_factor
    r_squared = (cov_factor_asset**2) / (var_factor * var_asset) if var_asset > _STD_DEV_EPSILON else 0.0

    # Standard OLS standard error of beta, derived from quantities already
    # computed above (no new statistical method introduced): total sum of
    # squares for asset = var_asset * (n-1); residual sum of squares =
    # (1 - r_squared) * that; residual variance uses the (n-2) denominator
    # (two parameters estimated: intercept, slope); SE(beta) = sqrt(
    # residual_variance / (var_factor * (n-1))), since sum((x-xbar)^2) =
    # var_factor * (n-1). This is what lets simulation-engine's propagation
    # logic build a genuine, computed uncertainty range around a scenario
    # impact rather than a hand-picked one.
    total_sum_squares_asset = var_asset * (n - 1)
    residual_sum_squares = (1 - r_squared) * total_sum_squares_asset
    residual_variance = residual_sum_squares / (n - 2)
    standard_error = (residual_variance / (var_factor * (n - 1))) ** 0.5

    confidence = ConfidenceLevel.MODERATE if n >= _ROBUST_OBSERVATIONS_THRESHOLD else ConfidenceLevel.LOW

    regime_clause = f" under regime {regime!r}" if regime else " (regime-unconditional)"
    return UAP(
        subject=f"factor sensitivity: {asset_id} to {factor_id}{regime_clause}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "sensitivity": beta,
            "method": "statistical-ols",
            "r_squared": r_squared,
            "standard_error": standard_error,
            "n_observations": n,
            "horizon": horizon,
            "regime": regime,
        },
        source="computed from the provided paired factor/asset return series",
        producer="quant-engine / factor sensitivity (statistical), PHASE E4 Part 3",
        confidence=confidence,
        assumptions=[
            "factor_returns and asset_returns are paired, aligned observations "
            "over the same periods, expressed in consistent units",
            "the historical relationship between factor and asset continues to "
            "hold going forward — never guaranteed, especially outside the "
            "regime this sample was drawn from",
        ],
        limitations=[
            f"n_observations={n}; a small sample increases estimation "
            "uncertainty even where the point estimate itself is unbiased",
            f"r_squared={r_squared:.3f} — a low value means the factor "
            "explains little of the asset's variance; the point sensitivity "
            "may not be a reliable driver even if computed correctly",
            "inherits covariance_matrix's own lack of estimation-error "
            "adjustment (no confidence interval around beta itself)",
        ],
        dependencies=[cov_uap.id],
        disagreement_set_ref=disagreement_set_ref,
    )


def duration_price_sensitivity(modified_duration: float, bond_id: str = "bond") -> UAP:
    """
    Deterministic bond-duration price sensitivity — standard closed-form
    approximation, no historical sample involved:

        ΔPrice/Price ≈ -ModifiedDuration × Δyield

    `modified_duration` must be non-negative (a bond's price cannot rise
    when yields rise under this approximation — a negative input would
    silently invert the standard relationship, which is never a genuine
    bond-duration figure).
    """
    if modified_duration < 0:
        raise ValueError(
            f"duration_price_sensitivity: modified_duration ({modified_duration!r}) "
            "must be non-negative — a bond's modified duration is a magnitude, "
            "not a signed figure; the formula's own minus sign already encodes "
            "the inverse price/yield relationship."
        )

    return UAP(
        subject=f"duration price sensitivity: {bond_id}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "sensitivity": -modified_duration,
            "method": "deterministic-duration",
            "modified_duration": modified_duration,
        },
        source="standard closed-form bond-duration approximation",
        producer="quant-engine / duration price sensitivity (deterministic), PHASE E4 Part 3",
        # MODERATE, not HIGH: the FORMULA is exact arithmetic, but it is
        # itself a first-order approximation of real bond price behaviour
        # (see limitations) — and validation_status is PROVISIONAL, which
        # caps confidence at MODERATE regardless (UAP's own guardrail).
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "modified_duration is itself accurate for the bond in question",
            "the yield change being evaluated is small enough that the "
            "linear (first-order) approximation remains reasonable",
        ],
        limitations=[
            "linear approximation only — convexity (the second-order "
            "curvature of the price/yield relationship) is not modelled; "
            "accuracy degrades for large yield moves",
            "assumes a parallel shift in the relevant yield — a curve "
            "reshaping (e.g. steepening without a parallel shift) is not "
            "captured by a single duration figure",
        ],
        dependencies=[],
    )
