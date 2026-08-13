"""
Temporal integrity — PHASE E3 brief, Part D: "proper time-series
validation; never randomly shuffle future/past financial data; implement
expanding or rolling windows, strict train/test time separation,
data-vintage awareness, as_of cutoffs. Historical models must only use
information actually available at the forecast timestamp."

Both split generators below are pure index arithmetic — no randomness,
no shuffling — so "no look-ahead" is a structural guarantee (every
training index is strictly less than its corresponding test index by
construction), not something asserted after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")


def expanding_window_splits(series: list[T], min_train: int, horizon: int = 1) -> Iterator[tuple[list[T], int]]:
    """
    Yields `(train, test_index)`: `train = series[:t]` (grows by one
    each step — "expanding"), `test_index` is the position in `series`
    being forecast, `horizon` steps past the end of `train`. `t` ranges
    over every value from `min_train` up to the last point that still
    leaves a valid `test_index` in range.
    """
    if min_train < 1:
        raise ValueError("expanding_window_splits: min_train must be >= 1.")
    if horizon < 1:
        raise ValueError("expanding_window_splits: horizon must be >= 1.")
    for t in range(min_train, len(series) - horizon + 1):
        yield series[:t], t + horizon - 1


def rolling_window_splits(series: list[T], window_size: int, horizon: int = 1) -> Iterator[tuple[list[T], int]]:
    """
    Yields `(train, test_index)`: `train = series[t - window_size : t]`
    — a FIXED-size window that slides forward (old observations drop off
    the front as new ones are added at the back), unlike the expanding
    variant which keeps everything. Useful when older data is suspected
    to reflect a stale regime rather than genuinely informative history.
    """
    if window_size < 1:
        raise ValueError("rolling_window_splits: window_size must be >= 1.")
    if horizon < 1:
        raise ValueError("rolling_window_splits: horizon must be >= 1.")
    for t in range(window_size, len(series) - horizon + 1):
        yield series[t - window_size : t], t + horizon - 1


def as_of_cutoff_index(timestamps: list[datetime], as_of: datetime) -> int:
    """The number of `timestamps` at or before `as_of` — i.e. the slice
    boundary `series[:as_of_cutoff_index(...)]` a forecaster made AT
    `as_of` may legitimately see. Strict: a timestamp exactly equal to
    `as_of` IS included (it was genuinely available at that instant);
    anything later is not, however close."""
    return sum(1 for ts in timestamps if ts <= as_of)


@dataclass(frozen=True)
class WalkForwardResult:
    predicted: list[float]
    actual: list[float]
    test_indices: list[int]


def walk_forward_backtest(
    series: list[float],
    model_fn: Callable[[list[float]], float],
    min_train: int,
    horizon: int = 1,
    window_size: int | None = None,
) -> WalkForwardResult:
    """
    Runs `model_fn` (any of this package's baseline/model forecast
    functions, which all share the `history -> float` signature) across
    every split from `expanding_window_splits` (default) or
    `rolling_window_splits` (if `window_size` given), collecting
    predicted-vs-actual pairs — the raw material `evaluation-engine`'s
    metrics functions consume once wrapped in `ForecastRecord`s (see
    `examples.py`/tests for that wiring).
    """
    splits = (
        rolling_window_splits(series, window_size, horizon)
        if window_size is not None
        else expanding_window_splits(series, min_train, horizon)
    )
    predicted, actual, test_indices = [], [], []
    for train, test_index in splits:
        predicted.append(model_fn(train))
        actual.append(series[test_index])
        test_indices.append(test_index)
    return WalkForwardResult(predicted=predicted, actual=actual, test_indices=test_indices)
