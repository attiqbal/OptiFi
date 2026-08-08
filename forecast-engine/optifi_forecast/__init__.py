"""
optifi_forecast — forecast-engine.

Implements the ensemble/aggregation mechanism from FORECAST_ENGINE_SPEC.md
Section 6 — the mechanism ANALYTICAL_CONTRACT_SPEC.md deferred back in
Phase 1B. This package implements only the *combination* of already-produced
forecasts; it does not implement, choose, or stub any econometric, ML, or
market-implied forecasting model (FORECAST_ENGINE_SPEC.md Section 5
deliberately leaves model choice undecided, and this package leaves it
exactly as undecided).
"""

from .ensemble import inverse_error_weighted_ensemble, simple_average_ensemble

__all__ = ["simple_average_ensemble", "inverse_error_weighted_ensemble"]
