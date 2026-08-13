"""
End-to-end integration — Testing Requirement: "model baseline
comparison." Runs a genuine walk-forward backtest (Part D) of a
competing model against a baseline (Part B) on the macro CPI target
(Part A), scores both with real evaluation-engine metrics (Part E), and
builds a scorecard (Part H) whose eligibility reflects whatever the
comparison actually found — this test does NOT hard-code which one wins;
Part B's own rule ("a complicated model that cannot beat a simple
baseline adds no demonstrated value") means the scorecard mechanism must
work correctly in EITHER direction, and on this project's own synthetic
CPI series the naive baseline is in fact difficult to beat (see the
Phase E3 deliverable's Empirical Results / Limitations sections) — this
test asserts that finding is surfaced correctly, not overridden.
"""

from datetime import datetime, timezone

from optifi_evaluation import build_scorecard, Eligibility, ForecastKind, ForecastRecord, point_forecast_metrics

from optifi_forecast import (
    exponential_smoothing_forecast,
    latest_observation_baseline,
    MACRO_CPI_TARGET,
    synthetic_cpi_yoy_series,
    walk_forward_backtest,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
WINDOW = (datetime(2021, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc))


def _to_records(predicted: list[float], actual: list[float], model_id: str) -> list[ForecastRecord]:
    records = []
    for p, a in zip(predicted, actual, strict=True):
        record = ForecastRecord(
            forecast_packet_id=f"{model_id}-{len(records)}",
            target=MACRO_CPI_TARGET.subject,
            forecast_timestamp=NOW,
            horizon=MACRO_CPI_TARGET.horizon,
            forecast_kind=ForecastKind.POINT,
            predicted_point=p,
            model_id=model_id,
            model_version="v1",
        ).record_outcome(a, realised_at=NOW)
        records.append(record)
    return records


def test_baseline_and_model_are_backtested_and_scored_on_the_same_series():
    series = synthetic_cpi_yoy_series()

    baseline_backtest = walk_forward_backtest(series, latest_observation_baseline, min_train=12)
    model_backtest = walk_forward_backtest(series, exponential_smoothing_forecast, min_train=12)

    # Same walk-forward split shape for both — a fair comparison, not
    # two differently-sized samples.
    assert len(baseline_backtest.predicted) == len(model_backtest.predicted)
    assert baseline_backtest.test_indices == model_backtest.test_indices

    baseline_records = _to_records(baseline_backtest.predicted, baseline_backtest.actual, "baseline-latest-obs")
    model_records = _to_records(model_backtest.predicted, model_backtest.actual, "econometric-ses")

    baseline_metrics = point_forecast_metrics(baseline_records)
    model_metrics = point_forecast_metrics(model_records)

    assert baseline_metrics.n == model_metrics.n > 0
    assert baseline_metrics.mae > 0
    assert model_metrics.mae > 0

    scorecard = build_scorecard(
        model_id="econometric-ses",
        model_version="v1",
        target=MACRO_CPI_TARGET.subject,
        horizon=MACRO_CPI_TARGET.horizon,
        training_window=WINDOW,
        evaluation_period=WINDOW,
        primary_metric_name="MAE",
        primary_metric_value=model_metrics.mae,
        higher_is_better=False,
        baseline_metric_value=baseline_metrics.mae,
        n_evaluated=model_metrics.n,
        last_evaluation=NOW,
        now=NOW,
    )

    # The scorecard's own beats_baseline()/eligibility must agree with a
    # direct comparison of the two real MAE figures — no independent,
    # possibly-inconsistent computation path.
    assert scorecard.beats_baseline() == (model_metrics.mae < baseline_metrics.mae)
    if model_metrics.mae < baseline_metrics.mae:
        assert scorecard.eligibility == Eligibility.ELIGIBLE
    else:
        assert scorecard.eligibility in (Eligibility.PROBATION, Eligibility.RETIRED)


def test_multiple_competing_models_produce_genuinely_different_backtest_results():
    """Part C: 'do not create one OptiFi forecasting model' — proven by
    showing the model families' predictions on the same series/splits
    are not identical."""
    from optifi_forecast import simple_ar1_baseline

    series = synthetic_cpi_yoy_series()
    ses_backtest = walk_forward_backtest(series, exponential_smoothing_forecast, min_train=12)
    ar1_backtest = walk_forward_backtest(series, simple_ar1_baseline, min_train=12)

    assert ses_backtest.predicted != ar1_backtest.predicted
