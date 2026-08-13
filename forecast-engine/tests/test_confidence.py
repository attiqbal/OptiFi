"""
Part F confidence calibration — every downgrade path, plus the
structural guarantee that HIGH is never returned.
"""

from datetime import datetime, timezone

from optifi_evaluation import build_scorecard, Eligibility
from optifi_shared import ConfidenceLevel, ValidationStatus

from optifi_forecast import calibrate_confidence

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)
WINDOW = (datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 7, 1, tzinfo=timezone.utc))


def _eligible_scorecard(**overrides):
    defaults = dict(
        model_id="econometric-ses",
        model_version="v1",
        target="test target",
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


def test_best_case_is_moderate_never_high():
    scorecard = _eligible_scorecard()
    confidence, reasons = calibrate_confidence(
        scorecard=scorecard,
        disagreement_relative_spread=0.05,
        horizon="3-month",
        input_validation_status=ValidationStatus.VERIFIED,
    )
    assert confidence == ConfidenceLevel.MODERATE
    assert reasons


def test_non_verified_input_forces_low():
    confidence, reasons = calibrate_confidence(
        scorecard=_eligible_scorecard(),
        disagreement_relative_spread=0.05,
        horizon="3-month",
        input_validation_status=ValidationStatus.PROVISIONAL,
    )
    assert confidence == ConfidenceLevel.LOW
    assert "PROVISIONAL" in reasons[0]


def test_out_of_distribution_forces_low():
    confidence, _ = calibrate_confidence(
        scorecard=_eligible_scorecard(),
        disagreement_relative_spread=0.05,
        horizon="3-month",
        input_validation_status=ValidationStatus.VERIFIED,
        is_out_of_distribution=True,
    )
    assert confidence == ConfidenceLevel.LOW


def test_no_scorecard_forces_low():
    confidence, reasons = calibrate_confidence(
        scorecard=None,
        disagreement_relative_spread=0.05,
        horizon="3-month",
        input_validation_status=ValidationStatus.VERIFIED,
    )
    assert confidence == ConfidenceLevel.LOW
    assert "no historical performance scorecard" in reasons[0]


def test_probation_scorecard_forces_low():
    scorecard = _eligible_scorecard(primary_metric_value=0.6, baseline_metric_value=0.5)  # fails baseline
    assert scorecard.eligibility == Eligibility.PROBATION
    confidence, _ = calibrate_confidence(
        scorecard=scorecard,
        disagreement_relative_spread=0.05,
        horizon="3-month",
        input_validation_status=ValidationStatus.VERIFIED,
    )
    assert confidence == ConfidenceLevel.LOW


def test_poor_regime_match_forces_low():
    scorecard = _eligible_scorecard(regimes_poor=("high-inflation-shock",))
    confidence, reasons = calibrate_confidence(
        scorecard=scorecard,
        disagreement_relative_spread=0.05,
        horizon="3-month",
        input_validation_status=ValidationStatus.VERIFIED,
        current_regime="high-inflation-shock",
    )
    assert confidence == ConfidenceLevel.LOW
    assert "regime" in reasons[0]


def test_strong_disagreement_forces_low():
    """'Do not equate model agreement with truth' — but also, genuine
    disagreement is itself evidence of uncertainty."""
    confidence, reasons = calibrate_confidence(
        scorecard=_eligible_scorecard(),
        disagreement_relative_spread=0.75,
        horizon="3-month",
        input_validation_status=ValidationStatus.VERIFIED,
    )
    assert confidence == ConfidenceLevel.LOW
    assert "disagreement" in reasons[0]


def test_long_horizon_forces_low():
    confidence, reasons = calibrate_confidence(
        scorecard=_eligible_scorecard(horizon="12-month"),
        disagreement_relative_spread=0.05,
        horizon="12-month",
        input_validation_status=ValidationStatus.VERIFIED,
    )
    assert confidence == ConfidenceLevel.LOW
    assert "horizon" in reasons[0]


def test_short_horizon_in_months_under_threshold_is_not_penalised():
    confidence, _ = calibrate_confidence(
        scorecard=_eligible_scorecard(horizon="3-month"),
        disagreement_relative_spread=0.05,
        horizon="3-month",
        input_validation_status=ValidationStatus.VERIFIED,
    )
    assert confidence == ConfidenceLevel.MODERATE


def test_confidence_never_returns_high_across_many_favourable_inputs():
    """Structural guarantee, not just a spot check — no combination of
    inputs, however favourable, should ever produce HIGH."""
    for spread in (0.0, 0.01, 0.29):
        for horizon in ("1-month", "3-month", "6-month"):
            confidence, _ = calibrate_confidence(
                scorecard=_eligible_scorecard(horizon=horizon),
                disagreement_relative_spread=spread,
                horizon=horizon,
                input_validation_status=ValidationStatus.VERIFIED,
            )
            assert confidence != ConfidenceLevel.HIGH
