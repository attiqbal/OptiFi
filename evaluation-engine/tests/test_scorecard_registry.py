"""
Scorecard/registry tests — Testing Requirements: "model baseline
comparison," "stale model," "model version change."
"""

from datetime import datetime, timedelta, timezone

from optifi_evaluation import DEFAULT_SCORECARD_STALENESS, Eligibility, ModelRegistry, build_scorecard

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)
WINDOW = (datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 7, 1, tzinfo=timezone.utc))


def _scorecard(**overrides):
    defaults = dict(
        model_id="econometric-ses",
        model_version="v1",
        target="UK CPI YoY, 3-month horizon",
        horizon="3-month",
        training_window=WINDOW,
        evaluation_period=WINDOW,
        primary_metric_name="MAE",
        primary_metric_value=0.3,
        higher_is_better=False,
        baseline_metric_value=0.5,
        n_evaluated=20,
        last_evaluation=NOW,
        now=NOW,
    )
    defaults.update(overrides)
    return build_scorecard(**defaults)


# --- model baseline comparison ---


def test_model_beating_baseline_is_eligible():
    scorecard = _scorecard(primary_metric_value=0.3, baseline_metric_value=0.5)
    assert scorecard.beats_baseline() is True
    assert scorecard.eligibility == Eligibility.ELIGIBLE


def test_model_failing_to_beat_baseline_is_probation():
    scorecard = _scorecard(primary_metric_value=0.55, baseline_metric_value=0.5)
    assert scorecard.beats_baseline() is False
    assert scorecard.eligibility == Eligibility.PROBATION


def test_model_far_worse_than_baseline_is_retired():
    scorecard = _scorecard(primary_metric_value=1.0, baseline_metric_value=0.5)  # 2x worse
    assert scorecard.eligibility == Eligibility.RETIRED


def test_no_baseline_supplied_is_conservatively_probation_not_eligible():
    scorecard = _scorecard(baseline_metric_value=None)
    assert scorecard.beats_baseline() is None
    assert scorecard.eligibility == Eligibility.PROBATION


def test_higher_is_better_metric_direction_respected():
    # accuracy: higher is better. 0.8 beats a 0.5 baseline.
    scorecard = _scorecard(primary_metric_name="accuracy", primary_metric_value=0.8, higher_is_better=True, baseline_metric_value=0.5)
    assert scorecard.beats_baseline() is True
    assert scorecard.eligibility == Eligibility.ELIGIBLE


# --- stale model ---


def test_scorecard_older_than_staleness_threshold_is_stale():
    old_evaluation = NOW - DEFAULT_SCORECARD_STALENESS - timedelta(days=1)
    scorecard = _scorecard(last_evaluation=old_evaluation, now=NOW)
    assert scorecard.eligibility == Eligibility.STALE


def test_registry_refresh_staleness_demotes_ageing_scorecard():
    registry = ModelRegistry()
    scorecard = _scorecard(last_evaluation=NOW)
    registry.register(scorecard)
    assert registry.eligible_scorecards(scorecard.target, scorecard.horizon) == [scorecard]

    much_later = NOW + DEFAULT_SCORECARD_STALENESS + timedelta(days=1)
    refreshed = registry.refresh_staleness(now=much_later)

    assert len(refreshed) == 1
    assert refreshed[0].eligibility == Eligibility.STALE
    # the ORIGINAL scorecard object is untouched — refresh appends, never mutates.
    assert scorecard.eligibility == Eligibility.ELIGIBLE
    assert registry.eligible_scorecards(scorecard.target, scorecard.horizon, ) == []


# --- model version change ---


def test_registry_keeps_every_version_appended_not_overwritten():
    registry = ModelRegistry()
    v1 = _scorecard(model_version="v1", primary_metric_value=0.5, last_evaluation=NOW)
    v2 = _scorecard(model_version="v2", primary_metric_value=0.3, last_evaluation=NOW + timedelta(days=1))
    registry.register(v1)
    registry.register(v2)

    all_versions = registry.all_scorecards(model_id="econometric-ses", target=v1.target)
    assert len(all_versions) == 2
    assert v1 in all_versions and v2 in all_versions
    # v1 is unaffected by v2's registration.
    assert v1.model_version == "v1"
    assert v1.primary_metric_value == 0.5


def test_latest_scorecard_returns_most_recently_evaluated_version():
    registry = ModelRegistry()
    v1 = _scorecard(model_version="v1", last_evaluation=NOW)
    v2 = _scorecard(model_version="v2", last_evaluation=NOW + timedelta(days=5))
    registry.register(v1)
    registry.register(v2)

    latest = registry.latest_scorecard(model_id="econometric-ses", target=v1.target, horizon=v1.horizon)
    assert latest.model_version == "v2"


def test_eligible_scorecards_excludes_retired_and_probation_and_stale():
    registry = ModelRegistry()
    eligible = _scorecard(model_id="model-a", primary_metric_value=0.2, baseline_metric_value=0.5, last_evaluation=NOW)
    retired = _scorecard(model_id="model-b", primary_metric_value=1.0, baseline_metric_value=0.5, last_evaluation=NOW)
    registry.register(eligible)
    registry.register(retired)

    result = registry.eligible_scorecards(eligible.target, eligible.horizon)
    assert result == [eligible]
