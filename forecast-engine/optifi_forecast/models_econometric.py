"""
Econometric model family — PHASE E3 brief, Part C / FORECAST_ENGINE_SPEC.md
Section 5: "statistical models fit to historical data."

Simple exponential smoothing (SES), deliberately a different technique
from `baselines.simple_ar1_baseline` (not the same formula re-labelled) —
Part C: "Build multiple model families per target... do not create one
'OptiFi forecasting model.'" SES weights all past observations
geometrically rather than fitting a single fixed lag coefficient, giving
genuinely different (and, on a trending or slowly mean-reverting series,
often better) behaviour.
"""

from __future__ import annotations

import numpy as np

_ALPHA_GRID = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def _fit_ses(history: list[float], alpha: float) -> tuple[list[float], float]:
    """Returns (level_path, in_sample_sse) for one candidate alpha —
    level_path[t] is the smoothed level AFTER incorporating history[t],
    used as the one-step-ahead forecast for history[t+1]."""
    level = history[0]
    level_path = [level]
    sse = 0.0
    for t in range(1, len(history)):
        forecast_for_t = level_path[-1]
        sse += (history[t] - forecast_for_t) ** 2
        level = alpha * history[t] + (1 - alpha) * level_path[-1]
        level_path.append(level)
    return level_path, sse


def fit_best_alpha(history: list[float], alpha_grid: list[float] = _ALPHA_GRID) -> float:
    """Grid search minimising in-sample one-step-ahead squared error —
    a deterministic statistical fit, not a hand-picked constant. Not a
    real hyperparameter-tuning framework (no cross-validation split of
    its own); `temporal.py`'s walk-forward harness is what actually
    prevents this from overfitting across the outer backtest."""
    if len(history) < 2:
        raise ValueError("fit_best_alpha: need at least 2 observations.")
    best_alpha, best_sse = alpha_grid[0], float("inf")
    for alpha in alpha_grid:
        _, sse = _fit_ses(history, alpha)
        if sse < best_sse:
            best_alpha, best_sse = alpha, sse
    return best_alpha


def exponential_smoothing_forecast(history: list[float], alpha: float | None = None) -> float:
    """One-step-ahead SES forecast. `alpha` fit via `fit_best_alpha` on
    `history` itself if not supplied — always fit ONLY on the history
    passed in, never on data beyond it (the caller's `temporal.py`
    truncation is what keeps this honest about as_of cutoffs)."""
    if not history:
        raise ValueError("exponential_smoothing_forecast: history is empty.")
    if len(history) == 1:
        return history[0]
    if alpha is None:
        alpha = fit_best_alpha(history)
    level_path, _ = _fit_ses(history, alpha)
    return level_path[-1]
