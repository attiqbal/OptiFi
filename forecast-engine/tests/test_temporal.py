"""
Part D temporal integrity — Testing Requirement: "rolling/expanding
window correctness." Direct, structural proof that train always
precedes test and nothing is shuffled.
"""

from datetime import datetime, timedelta, timezone

import pytest

from optifi_forecast import as_of_cutoff_index, expanding_window_splits, rolling_window_splits, walk_forward_backtest


def test_expanding_window_train_always_precedes_test():
    series = list(range(20))
    for train, test_index in expanding_window_splits(series, min_train=5):
        assert max(train) < series[test_index]
        assert len(train) == test_index  # for horizon=1, train is exactly series[:test_index]


def test_expanding_window_grows_monotonically():
    series = list(range(10))
    splits = list(expanding_window_splits(series, min_train=3))
    lengths = [len(train) for train, _ in splits]
    assert lengths == sorted(lengths)
    assert lengths == list(range(3, 10))


def test_expanding_window_respects_horizon():
    series = list(range(10))
    splits = list(expanding_window_splits(series, min_train=3, horizon=3))
    for train, test_index in splits:
        assert test_index == len(train) + 3 - 1


def test_rolling_window_has_constant_size():
    series = list(range(20))
    splits = list(rolling_window_splits(series, window_size=5))
    for train, _ in splits:
        assert len(train) == 5


def test_rolling_window_slides_forward_never_backward():
    series = list(range(20))
    splits = list(rolling_window_splits(series, window_size=5))
    starts = [train[0] for train, _ in splits]
    assert starts == sorted(starts)
    assert starts == list(range(len(starts)))


def test_no_split_ever_includes_the_test_point_or_beyond():
    """The structural no-look-ahead guarantee: for every split, every
    element of train has a smaller series-index than test_index."""
    series = [float(i) for i in range(30)]
    for train, test_index in expanding_window_splits(series, min_train=4):
        train_max_index = test_index - 1  # by construction for horizon=1
        assert train_max_index < test_index
        assert train == series[: train_max_index + 1]
    for train, test_index in rolling_window_splits(series, window_size=6):
        assert train == series[test_index - 6 : test_index]


def test_walk_forward_backtest_predicted_and_actual_are_aligned():
    series = [float(i) for i in range(15)]
    result = walk_forward_backtest(series, lambda h: h[-1], min_train=5)  # naive baseline
    for predicted, actual in zip(result.predicted, result.actual, strict=True):
        assert actual == predicted + 1.0  # naive lag-1 forecast on a pure ramp


def test_walk_forward_backtest_with_rolling_window():
    series = [float(i) for i in range(15)]
    result = walk_forward_backtest(series, lambda h: h[-1], min_train=5, window_size=4)
    assert len(result.predicted) == len(series) - 4


# --- as_of cutoff ---


def test_as_of_cutoff_index_includes_exactly_at_boundary():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(days=i) for i in range(5)]
    as_of = timestamps[2]
    assert as_of_cutoff_index(timestamps, as_of) == 3  # indices 0,1,2 <= as_of


def test_as_of_cutoff_index_excludes_future_timestamps():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(days=i) for i in range(5)]
    as_of = base - timedelta(days=1)  # before everything
    assert as_of_cutoff_index(timestamps, as_of) == 0
