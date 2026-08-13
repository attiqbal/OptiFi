"""
Machine-learning model family — PHASE E3 brief, Part C /
FORECAST_ENGINE_SPEC.md Section 5: "pattern-based models trained on
broader feature sets" (as opposed to the econometric family's single-lag
statistical form).

A linear regression over engineered lag/rolling/trend features — no
`sklearn`/`statsmodels` dependency exists in this project yet (every
other engine's numeric work uses `numpy`/`scipy` directly, e.g.
`quant-engine`'s covariance/VaR code), so this uses `numpy.linalg.lstsq`
directly rather than introduce a new heavy dependency for one model.
Genuinely distinct from the econometric family: multiple engineered
features combined via a fitted weight vector, not a single fixed-form
smoothing/lag equation — this is the actual "broader feature set" Section
5 names, not econometric-family AR(1)/SES relabelled.
"""

from __future__ import annotations

import numpy as np

from optifi_shared import InsufficientDataFailure

DEFAULT_ROLLING_WINDOW = 3
# Minimum number of training samples the regression is fit on — below
# this a 4-feature-plus-intercept linear fit is under-determined enough
# to be meaningless, not merely noisy.
MIN_TRAINING_SAMPLES = 5


def _build_features(history: list[float], window: int) -> tuple[np.ndarray, np.ndarray]:
    """Builds (X, y) training pairs: for each t from `window+1` to
    len(history)-1, y=history[t], X row = [1, lag1, lag2, rolling_mean,
    trend_index] — every feature built ONLY from history[:t] (strictly
    past information relative to the target), never from history[t]
    itself or beyond."""
    n = len(history)
    rows: list[list[float]] = []
    targets: list[float] = []
    for t in range(window + 1, n):
        lag1 = history[t - 1]
        lag2 = history[t - 2]
        rolling_mean = float(np.mean(history[t - window : t]))
        trend_index = float(t)
        rows.append([1.0, lag1, lag2, rolling_mean, trend_index])
        targets.append(history[t])
    return np.array(rows), np.array(targets)


def fit_linear_feature_model(history: list[float], window: int = DEFAULT_ROLLING_WINDOW) -> np.ndarray:
    """Returns the fitted coefficient vector [intercept, lag1, lag2,
    rolling_mean, trend_index] via ordinary least squares. Raises
    `InsufficientDataFailure` rather than silently fitting an
    under-determined/meaningless regression on too little data."""
    X, y = _build_features(history, window)
    if len(y) < MIN_TRAINING_SAMPLES:
        raise InsufficientDataFailure(
            f"fit_linear_feature_model: only {len(y)} training samples "
            f"available from {len(history)} history points (need at least "
            f"{MIN_TRAINING_SAMPLES})."
        )
    coefficients, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coefficients


def linear_feature_forecast(history: list[float], window: int = DEFAULT_ROLLING_WINDOW) -> float:
    """One-step-ahead forecast: fits on `history` (strictly past data
    only, per `_build_features`), then builds the feature vector for the
    NEXT step from the tail of `history` and applies the fitted weights."""
    coefficients = fit_linear_feature_model(history, window)
    lag1 = history[-1]
    lag2 = history[-2]
    rolling_mean = float(np.mean(history[-window:]))
    trend_index = float(len(history))
    feature_vector = np.array([1.0, lag1, lag2, rolling_mean, trend_index])
    return float(feature_vector @ coefficients)
