"""
optifi_forecast — forecast-engine.

Implements the ensemble/aggregation mechanism from FORECAST_ENGINE_SPEC.md
Section 6, and, since Phase E3, the real (if synthetic-data-backed)
forecasting capability itself: three selected targets (`targets.py`),
simple baselines (`baselines.py`), two competing model families
(`models_econometric.py`, `models_ml.py`), a temporal-integrity
walk-forward harness (`temporal.py`), confidence calibration wired to
`evaluation-engine`'s scorecards (`confidence.py`), performance-weighted
ensembling wired to those same scorecards (`ensemble_wiring.py`), and
frozen-forecast/model-version-change handling (`frozen.py`). It does not
implement, choose, or stub a full production model beyond what a real
forecasting problem needs to demonstrate genuine out-of-sample
evaluation — model SELECTION within each family remains real
data-science work, per FORECAST_ENGINE_SPEC.md Section 5.
"""

from .baselines import (
    historical_mean_baseline,
    latest_observation_baseline,
    market_implied_baseline,
    MARKET_IMPLIED_UNAVAILABLE_REASON,
    rolling_mean_baseline,
    simple_ar1_baseline,
)
from .confidence import calibrate_confidence
from .ensemble import inverse_error_weighted_ensemble, simple_average_ensemble
from .ensemble_wiring import performance_weighted_ensemble
from .frozen import new_forecast_supersedes_old
from .models_econometric import exponential_smoothing_forecast, fit_best_alpha
from .models_ml import fit_linear_feature_model, linear_feature_forecast
from .synthetic_data import (
    realised_volatility_series,
    revenue_growth_direction_labels,
    synthetic_company_revenue_growth,
    synthetic_cpi_yoy_series,
    synthetic_index_returns,
)
from .targets import (
    ALL_TARGETS,
    COMPANY_REVENUE_DIRECTION_TARGET,
    ForecastTarget,
    MACRO_CPI_TARGET,
    MARKET_VOLATILITY_TARGET,
)
from .temporal import (
    as_of_cutoff_index,
    expanding_window_splits,
    rolling_window_splits,
    walk_forward_backtest,
    WalkForwardResult,
)

__all__ = [
    "simple_average_ensemble",
    "inverse_error_weighted_ensemble",
    "performance_weighted_ensemble",
    "ForecastTarget",
    "MACRO_CPI_TARGET",
    "MARKET_VOLATILITY_TARGET",
    "COMPANY_REVENUE_DIRECTION_TARGET",
    "ALL_TARGETS",
    "synthetic_cpi_yoy_series",
    "synthetic_index_returns",
    "realised_volatility_series",
    "synthetic_company_revenue_growth",
    "revenue_growth_direction_labels",
    "latest_observation_baseline",
    "historical_mean_baseline",
    "rolling_mean_baseline",
    "simple_ar1_baseline",
    "market_implied_baseline",
    "MARKET_IMPLIED_UNAVAILABLE_REASON",
    "fit_best_alpha",
    "exponential_smoothing_forecast",
    "fit_linear_feature_model",
    "linear_feature_forecast",
    "expanding_window_splits",
    "rolling_window_splits",
    "as_of_cutoff_index",
    "walk_forward_backtest",
    "WalkForwardResult",
    "calibrate_confidence",
    "new_forecast_supersedes_old",
]
