"""
Testing Requirements: "zero/near-zero ensemble mean," "strongly
disagreeing forecasts" — exercised against this phase's own selected
targets (inflation forecasts genuinely can sit near zero; competing
models genuinely can disagree strongly), not abstract numbers.
"""

import math

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_forecast import MACRO_CPI_TARGET, simple_average_ensemble

DISAGREEMENT_SET_REF = "cpi-near-zero-disagreement"


def _forecast(result: float, producer: str) -> UAP:
    return UAP(
        subject=MACRO_CPI_TARGET.subject,
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="test",
        producer=producer,
        confidence=ConfidenceLevel.MODERATE,
        disagreement_set_ref=DISAGREEMENT_SET_REF,
    )


def test_near_zero_mean_ensemble_does_not_divide_by_zero_or_crash():
    """Three models forecasting inflation right around 0% — the
    ensemble's relative-spread confidence calculation divides by the
    mean, which is near zero here; must not raise or produce inf/nan."""
    forecasts = [_forecast(0.05, "m1"), _forecast(-0.03, "m2"), _forecast(0.01, "m3")]
    ensemble = simple_average_ensemble(forecasts)
    assert ensemble.result == pytest.approx((0.05 - 0.03 + 0.01) / 3)
    assert math.isfinite(ensemble.result)
    assert ensemble.confidence in (ConfidenceLevel.LOW, ConfidenceLevel.MODERATE)


def test_exactly_zero_mean_ensemble_does_not_crash():
    forecasts = [_forecast(1.0, "m1"), _forecast(-1.0, "m2")]
    ensemble = simple_average_ensemble(forecasts)
    assert ensemble.result == 0.0
    # a near-zero mean with meaningfully spread inputs is a genuine
    # disagreement case, not a numerical edge case that should crash.
    assert ensemble.confidence == ConfidenceLevel.LOW


def test_strongly_disagreeing_cpi_forecasts_preserve_disagreement_and_widen_uncertainty():
    """FORECAST_ENGINE_SPEC.md Section 6: 'low agreement between
    constituent models should widen the ensemble's uncertainty bounds,
    not narrow them through averaging alone.'"""
    strongly_disagreeing = [_forecast(1.0, "m1"), _forecast(5.0, "m2"), _forecast(9.0, "m3")]
    closely_agreeing = [_forecast(2.9, "m1"), _forecast(3.0, "m2"), _forecast(3.1, "m3")]

    disagreeing_ensemble = simple_average_ensemble(strongly_disagreeing)
    agreeing_ensemble = simple_average_ensemble(closely_agreeing)

    assert disagreeing_ensemble.confidence == ConfidenceLevel.LOW
    assert agreeing_ensemble.confidence == ConfidenceLevel.MODERATE
    # every individual model's forecast remains visible — disagreement is
    # never silently hidden inside the ensemble figure.
    assert set(disagreeing_ensemble.dependencies) == {f.id for f in strongly_disagreeing}
