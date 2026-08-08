"""
optifi_quant — quant-engine.

Implements portfolio and risk metrics from QUANT_ENGINE_SPEC.md Section 5.
This package currently implements Section 5.2's Sharpe ratio, Section
5.3's two Value-at-Risk methods (historical, parametric), and Section
5.5's correlation/covariance/portfolio-variance functions — every other
metric in Section 5 (returns, other risk-adjusted ratios,
exposure/concentration) and the Capital Efficiency sub-scores (Section
7/8) are separate, not-yet-implemented future work.
"""

from .covariance import correlation_matrix, covariance_matrix, portfolio_variance
from .risk_metrics import historical_var, parametric_var, sharpe_ratio

__all__ = [
    "sharpe_ratio",
    "historical_var",
    "parametric_var",
    "covariance_matrix",
    "correlation_matrix",
    "portfolio_variance",
]
