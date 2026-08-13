"""
Correlation, covariance, and portfolio variance — QUANT_ENGINE_SPEC.md,
Section 5.5. This is "the primary handoff to `optimisation-engine`" per
that section's own note — `covariance_matrix`'s result (plus expected
returns, not computed here) is what a future optimisation-engine consumes.

All three functions apply their guardrail from Section 9 ("Quantitative
Validation") and return a `UAP` with `information_class=ESTIMATE`.
"""

from __future__ import annotations

import numpy as np

from optifi_shared import ConfidenceLevel, InformationClass, InsufficientDataFailure, UAP, ValidationStatus

# QUANT_ENGINE_SPEC.md Section 9: covariance matrices must be positive
# semi-definite. Eigenvalues are allowed to dip as low as -_PSD_TOLERANCE
# to absorb floating-point noise around zero (a mathematically PSD matrix
# can compute an eigenvalue like -1e-16 due to rounding) — this is not a
# relaxation of the requirement, just a tolerance for how real floating
# point arithmetic behaves.
_PSD_TOLERANCE = 1e-8

# A genuine sample standard deviation of exactly (or near) zero means a
# constant return series, for which correlation is mathematically
# undefined (division by zero).
_STD_DEV_EPSILON = 1e-12

# Section 9: portfolio weights must sum to 1.0. Floating-point-safe
# tolerance, not exact equality.
_WEIGHTS_SUM_TOLERANCE = 1e-6


def _validate_returns_by_asset(
    returns_by_asset: dict[str, list[float]], fn_name: str
) -> tuple[list[str], int]:
    if len(returns_by_asset) < 2:
        # Phase E1 hardening: InsufficientDataFailure IS a ValueError,
        # so every pre-existing `pytest.raises(ValueError)` still
        # matches — this also lets a caller branch on the specific,
        # machine-readable category.
        raise InsufficientDataFailure(
            f"{fn_name}: at least 2 assets are required, got "
            f"{len(returns_by_asset)}."
        )

    asset_names = list(returns_by_asset.keys())
    lengths = {name: len(series) for name, series in returns_by_asset.items()}
    unique_lengths = set(lengths.values())
    if len(unique_lengths) != 1:
        raise ValueError(
            f"{fn_name}: all return series must be the same length "
            f"(aligned time periods); got {lengths}."
        )

    n = unique_lengths.pop()
    if n < 2:
        raise InsufficientDataFailure(
            f"{fn_name}: each return series must have at least 2 "
            f"observations to compute a sample statistic, got {n}."
        )

    return asset_names, n


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _sample_covariance(x: list[float], y: list[float]) -> float:
    """Sample covariance (n-1 denominator), the standard unbiased estimator."""
    n = len(x)
    mean_x = _mean(x)
    mean_y = _mean(y)
    # strict=True: x and y are always the same length via
    # _validate_returns_by_asset's own check before this is ever called,
    # but a silent truncation on a future mismatch would produce a
    # quietly wrong covariance number rather than a clear error.
    return sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y, strict=True)) / (n - 1)


def _is_positive_semi_definite(
    matrix: dict[str, dict[str, float]],
    asset_order: list[str],
    tolerance: float = _PSD_TOLERANCE,
) -> bool:
    """
    Check positive semi-definiteness via eigenvalues of the symmetric
    matrix. A genuine sample covariance matrix computed from real return
    data is always PSD by construction (it is Gram-matrix-like); this
    check is a real, independent verification per QUANT_ENGINE_SPEC.md
    Section 9, not a formality — see tests/test_covariance.py for a
    deliberately-constructed non-PSD matrix that proves it actually fires.
    """
    array = np.array([[matrix[a][b] for b in asset_order] for a in asset_order])
    eigenvalues = np.linalg.eigvalsh(array)
    return bool(np.all(eigenvalues >= -tolerance))


def covariance_matrix(returns_by_asset: dict[str, list[float]]) -> UAP:
    """
    Sample covariance matrix across multiple assets' return series
    (QUANT_ENGINE_SPEC.md, Section 5.5).
    """
    asset_names, _ = _validate_returns_by_asset(returns_by_asset, "covariance_matrix")

    matrix: dict[str, dict[str, float]] = {
        a: {b: _sample_covariance(returns_by_asset[a], returns_by_asset[b]) for b in asset_names}
        for a in asset_names
    }

    if not _is_positive_semi_definite(matrix, asset_names):
        raise ValueError(
            "covariance_matrix: the computed covariance matrix is not "
            "positive semi-definite (QUANT_ENGINE_SPEC.md Section 9) — "
            "portfolio variance calculations built on it would be "
            "meaningless. This should not occur for a genuine sample "
            "covariance matrix computed from real, non-degenerate return "
            "data; if it does, check the input for duplicated or "
            "corrupted return series."
        )

    return UAP(
        subject=f"covariance matrix: {', '.join(asset_names)}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=matrix,
        source="computed from the provided per-asset return series",
        producer="quant-engine / covariance matrix, QUANT_ENGINE_SPEC.md Section 5.5",
        # MODERATE: the sample-covariance formula is standard and
        # deterministic (not LOW), but the result is only as good as the
        # provided sample's representativeness, which this function
        # cannot itself verify (not HIGH).
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "each asset's return series covers the same, aligned time "
            "periods with no missing values",
            "returns are expressed in consistent units across assets",
        ],
        limitations=[
            "sample covariance is sensitive to sample size and outliers, "
            "and carries no adjustment for estimation error",
        ],
        dependencies=[],
    )


def correlation_matrix(returns_by_asset: dict[str, list[float]]) -> UAP:
    """
    Correlation matrix: rho(X,Y) = Cov(X,Y) / (sigma_X * sigma_Y)
    (QUANT_ENGINE_SPEC.md, Section 5.5).
    """
    asset_names, _ = _validate_returns_by_asset(returns_by_asset, "correlation_matrix")

    variances = {a: _sample_covariance(returns_by_asset[a], returns_by_asset[a]) for a in asset_names}
    std_devs = {a: variance**0.5 for a, variance in variances.items()}

    for asset, std_dev in std_devs.items():
        if std_dev < _STD_DEV_EPSILON:
            raise ValueError(
                f"correlation_matrix: asset '{asset}' has a zero or "
                f"near-zero standard deviation ({std_dev!r}); correlation "
                "is undefined for a constant return series."
            )

    matrix: dict[str, dict[str, float]] = {
        a: {
            b: _sample_covariance(returns_by_asset[a], returns_by_asset[b])
            / (std_devs[a] * std_devs[b])
            for b in asset_names
        }
        for a in asset_names
    }

    return UAP(
        subject=f"correlation matrix: {', '.join(asset_names)}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=matrix,
        source="computed from the provided per-asset return series",
        producer="quant-engine / correlation matrix, QUANT_ENGINE_SPEC.md Section 5.5",
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "each asset's return series covers the same, aligned time "
            "periods with no missing values",
        ],
        limitations=[
            "sample correlation is sensitive to sample size and outliers, "
            "and can be unstable for short return series",
        ],
        dependencies=[],
    )


def portfolio_variance(
    weights: dict[str, float],
    covariance: dict[str, dict[str, float]],
) -> UAP:
    """
    Portfolio variance: sigma_p^2 = w^T Sigma w (QUANT_ENGINE_SPEC.md,
    Section 5.5).
    """
    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > _WEIGHTS_SUM_TOLERANCE:
        raise ValueError(
            f"portfolio_variance: weights must sum to 1.0 within a "
            f"tolerance of {_WEIGHTS_SUM_TOLERANCE}; got sum={weight_sum!r}."
        )

    weight_assets = set(weights.keys())
    covariance_assets = set(covariance.keys())
    if weight_assets != covariance_assets:
        raise ValueError(
            "portfolio_variance: the assets in `weights` and `covariance` "
            f"must match exactly; weights has {sorted(weight_assets)}, "
            f"covariance has {sorted(covariance_assets)}."
        )
    for asset, row in covariance.items():
        row_assets = set(row.keys())
        if row_assets != covariance_assets:
            raise ValueError(
                f"portfolio_variance: covariance matrix row '{asset}' "
                f"does not cover exactly the same asset set as the "
                f"matrix's own keys; expected {sorted(covariance_assets)}, "
                f"got {sorted(row_assets)}."
            )

    asset_order = sorted(weight_assets)
    variance = sum(
        weights[a] * weights[b] * covariance[a][b]
        for a in asset_order
        for b in asset_order
    )

    return UAP(
        subject=f"portfolio variance: {', '.join(asset_order)}",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=variance,
        source="computed from the provided weights and covariance matrix",
        producer="quant-engine / portfolio variance, QUANT_ENGINE_SPEC.md Section 5.5",
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "weights and covariance are expressed over the same period "
            "and in consistent units",
        ],
        limitations=[
            "portfolio variance computed this way inherits every "
            "limitation of the underlying covariance matrix (sample-size "
            "sensitivity, no estimation-error adjustment)",
        ],
        dependencies=[],
    )
