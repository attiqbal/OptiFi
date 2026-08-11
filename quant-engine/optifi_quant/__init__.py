"""
optifi_quant — quant-engine.

Implements portfolio and risk metrics from QUANT_ENGINE_SPEC.md Section 5,
plus the Capital Efficiency Score (Section 7's six sub-scores and Section
8's composite). This package currently implements Section 5.2's Sharpe
ratio, Section 5.3's two Value-at-Risk methods (historical, parametric),
Section 5.5's correlation/covariance/portfolio-variance functions, and the
Capital Efficiency Score — every other metric in Section 5 (returns, other
risk-adjusted ratios, exposure/concentration) remains separate,
not-yet-implemented future work.
"""

from .capital_efficiency import (
    cash_efficiency,
    composite_capital_efficiency_score,
    debt_efficiency,
    investment_efficiency,
    liquidity_efficiency,
    risk_efficiency,
    tax_efficiency,
)
from .covariance import correlation_matrix, covariance_matrix, portfolio_variance
from .risk_metrics import historical_var, parametric_var, sharpe_ratio

__all__ = [
    "sharpe_ratio",
    "historical_var",
    "parametric_var",
    "covariance_matrix",
    "correlation_matrix",
    "portfolio_variance",
    "cash_efficiency",
    "debt_efficiency",
    "risk_efficiency",
    "tax_efficiency",
    "liquidity_efficiency",
    "investment_efficiency",
    "composite_capital_efficiency_score",
]
