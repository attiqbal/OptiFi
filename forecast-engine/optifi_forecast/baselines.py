"""
Baselines — PHASE E3 brief, Part B: "For every problem, create simple
baselines before sophisticated models... A complicated model that cannot
beat a simple baseline adds no demonstrated value."

Every baseline below takes `history: list[float]` — the data GENUINELY
available at forecast time (the caller's own responsibility to truncate
correctly; see `temporal.py` for the walk-forward harness that does this)
— and returns a single next-step point forecast. Deterministic,
statistical arithmetic only, per this project's own rule ("do not use an
LLM for calculations deterministic/statistical systems can perform more
reliably") — nothing here is a model in the Part C sense, each is
deliberately as simple as the brief's own named list.
"""

from __future__ import annotations

import numpy as np

from optifi_shared import UnsupportedFailure

DEFAULT_ROLLING_WINDOW = 12

MARKET_IMPLIED_UNAVAILABLE_REASON = (
    "market-implied expectation baseline unavailable: no options-pricing or "
    "yield-curve data source is connected (DATA_SOURCE_REGISTRY.md Section "
    "7.1 — every Category A market-data adapter is NOT CONNECTED). Rather "
    "than fabricate a market-implied figure from unrelated data, this "
    "baseline is explicitly withheld — see the Phase E3 deliverable's "
    "Limitations section."
)


def latest_observation_baseline(history: list[float]) -> float:
    """The naive forecast: tomorrow = today. The bar every other model,
    baseline or not, must clear to be worth anything."""
    if not history:
        raise ValueError("latest_observation_baseline: history is empty.")
    return history[-1]


def historical_mean_baseline(history: list[float]) -> float:
    """Expanding-window mean of everything seen so far."""
    if not history:
        raise ValueError("historical_mean_baseline: history is empty.")
    return float(np.mean(history))


def rolling_mean_baseline(history: list[float], window: int = DEFAULT_ROLLING_WINDOW) -> float:
    """Mean of the most recent `window` observations only — responds to
    recent regime shifts unlike the full-history mean, at the cost of
    more variance."""
    if not history:
        raise ValueError("rolling_mean_baseline: history is empty.")
    return float(np.mean(history[-window:]))


def simple_ar1_baseline(history: list[float]) -> float:
    """
    Closed-form OLS AR(1): x_t = c + phi * x_{t-1} + eps_t, fit on every
    consecutive pair in `history`, forecasting one step past the last
    observation. Falls back to `latest_observation_baseline` when fewer
    than 3 points are available (two pairs is the minimum for a
    non-degenerate OLS fit) — an explicit, documented degenerate case,
    not a silent divide-by-zero.
    """
    if len(history) < 3:
        return latest_observation_baseline(history)
    x_prev = np.array(history[:-1])
    x_curr = np.array(history[1:])
    design = np.vstack([np.ones_like(x_prev), x_prev]).T
    coefficients, *_ = np.linalg.lstsq(design, x_curr, rcond=None)
    c, phi = coefficients
    return float(c + phi * history[-1])


def market_implied_baseline(*_args, **_kwargs) -> float:
    """Deliberately unimplemented — see MARKET_IMPLIED_UNAVAILABLE_REASON.
    Raises rather than returning a plausible-looking number, per this
    project's 'never fabricate unavailable financial information' rule."""
    raise UnsupportedFailure(MARKET_IMPLIED_UNAVAILABLE_REASON)
