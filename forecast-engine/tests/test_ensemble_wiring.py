"""
Part G — comparing equal-weight vs. performance-weighted ensembles, with
the performance weights sourced from real `evaluation-engine` scorecards
rather than a hand-assembled error list. Also: Part H's "a poor-
performing model should be capable of losing weight or being retired,"
proven directly (a RETIRED model is excluded entirely).
"""

from datetime import datetime, timezone

import pytest
from optifi_evaluation import build_scorecard
from optifi_shared import ConfidenceLevel, InformationClass, InsufficientDataFailure, UAP, ValidationStatus

from optifi_forecast import performance_weighted_ensemble, simple_average_ensemble

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)
WINDOW = (datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 7, 1, tzinfo=timezone.utc))
SUBJECT = "test target"
DISAGREEMENT_SET_REF = "test-disagreement-set"


def _forecast(result: float, model_id: str) -> UAP:
    return UAP(
        subject=SUBJECT,
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="test",
        producer=f"forecast-engine / {model_id}",
        confidence=ConfidenceLevel.MODERATE,
        disagreement_set_ref=DISAGREEMENT_SET_REF,
    )


def _scorecard(model_id: str, mae: float, eligibility_metric_baseline: float = 0.5):
    return build_scorecard(
        model_id=model_id,
        model_version="v1",
        target=SUBJECT,
        horizon="3-month",
        training_window=WINDOW,
        evaluation_period=WINDOW,
        primary_metric_name="MAE",
        primary_metric_value=mae,
        higher_is_better=False,
        baseline_metric_value=eligibility_metric_baseline,
        n_evaluated=20,
        last_evaluation=NOW,
        now=NOW,
    )


def test_equal_weight_and_performance_weighted_disagree_when_models_differ_in_skill():
    forecasts = [_forecast(10.0, "econometric-ses"), _forecast(20.0, "ml-linear")]
    scorecards = {
        "econometric-ses": _scorecard("econometric-ses", mae=0.1),  # much more accurate
        "ml-linear": _scorecard("ml-linear", mae=0.4),
    }

    equal = simple_average_ensemble(forecasts)
    performance = performance_weighted_ensemble(forecasts, ["econometric-ses", "ml-linear"], scorecards)

    assert equal.result == pytest.approx(15.0)
    # performance-weighted should sit closer to the more accurate model's 10.0
    assert performance.result < equal.result
    assert abs(performance.result - 10.0) < abs(equal.result - 10.0)


def test_retired_model_is_excluded_entirely_not_merely_down_weighted():
    forecasts = [_forecast(10.0, "good-model"), _forecast(1000.0, "bad-model")]
    scorecards = {
        "good-model": _scorecard("good-model", mae=0.1, eligibility_metric_baseline=0.5),
        # far worse than baseline -> RETIRED
        "bad-model": _scorecard("bad-model", mae=5.0, eligibility_metric_baseline=0.5),
    }
    with pytest.raises(InsufficientDataFailure):
        # only one non-retired model remains — too few for a meaningful ensemble.
        performance_weighted_ensemble(forecasts, ["good-model", "bad-model"], scorecards)


def test_retired_model_excluded_leaves_only_eligible_models_weighted():
    forecasts = [_forecast(10.0, "good-model"), _forecast(12.0, "ok-model"), _forecast(1000.0, "bad-model")]
    scorecards = {
        "good-model": _scorecard("good-model", mae=0.1),
        "ok-model": _scorecard("ok-model", mae=0.3),
        "bad-model": _scorecard("bad-model", mae=5.0),  # RETIRED, excluded
    }
    result = performance_weighted_ensemble(
        forecasts, ["good-model", "ok-model", "bad-model"], scorecards
    )
    # result must be a blend of ONLY 10.0 and 12.0 — nowhere near 1000.
    assert 10.0 <= result.result <= 12.0


def test_model_with_no_scorecard_is_excluded():
    forecasts = [_forecast(10.0, "known-model"), _forecast(20.0, "unknown-model")]
    scorecards = {"known-model": _scorecard("known-model", mae=0.1)}
    with pytest.raises(InsufficientDataFailure):
        performance_weighted_ensemble(forecasts, ["known-model", "unknown-model"], scorecards)
