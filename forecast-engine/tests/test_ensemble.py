"""
Tests for forecast-engine's ensemble/aggregation mechanism
(FORECAST_ENGINE_SPEC.md, Section 6).
"""

import copy

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_forecast import inverse_error_weighted_ensemble, simple_average_ensemble

SUBJECT = "test subject"
DISAGREEMENT_SET_REF = "test-disagreement-set"


def _make_forecast(result: float, producer: str = "test model") -> UAP:
    return UAP(
        subject=SUBJECT,
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="test source",
        producer=producer,
        confidence=ConfidenceLevel.MODERATE,
        disagreement_set_ref=DISAGREEMENT_SET_REF,
    )


# --- simple_average_ensemble ---


def test_simple_average_correct_result_for_known_inputs():
    forecasts = [_make_forecast(0.30), _make_forecast(0.40), _make_forecast(0.50)]
    uap = simple_average_ensemble(forecasts)
    assert uap.result == pytest.approx(0.4)
    assert uap.information_class == InformationClass.ESTIMATE


def test_simple_average_dependencies_list_every_input_id():
    forecasts = [_make_forecast(0.30), _make_forecast(0.40), _make_forecast(0.50)]
    uap = simple_average_ensemble(forecasts)
    assert set(uap.dependencies) == {f.id for f in forecasts}
    assert len(uap.dependencies) == 3


def test_simple_average_disagreement_set_ref_matches_inputs():
    forecasts = [_make_forecast(0.30), _make_forecast(0.40)]
    uap = simple_average_ensemble(forecasts)
    assert uap.disagreement_set_ref == DISAGREEMENT_SET_REF


def test_simple_average_raises_on_mismatched_subject():
    mismatched = _make_forecast(0.40)
    mismatched.subject = "a different subject"  # only to construct an invalid input set; see mutation test below for the real no-mutation guarantee
    with pytest.raises(ValueError):
        simple_average_ensemble([_make_forecast(0.30), mismatched])


def test_simple_average_raises_when_disagreement_set_ref_missing():
    no_ref = UAP(
        subject=SUBJECT,
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=0.40,
        source="test source",
        producer="test model",
        confidence=ConfidenceLevel.MODERATE,
        # disagreement_set_ref intentionally omitted (defaults to None)
    )
    with pytest.raises(ValueError):
        simple_average_ensemble([_make_forecast(0.30), no_ref])


def test_simple_average_raises_when_disagreement_set_ref_not_shared():
    other_ref = _make_forecast(0.40)
    other_ref.disagreement_set_ref = "a-different-set"
    with pytest.raises(ValueError):
        simple_average_ensemble([_make_forecast(0.30), other_ref])


def test_simple_average_does_not_mutate_inputs():
    forecasts = [_make_forecast(0.30), _make_forecast(0.40), _make_forecast(0.50)]
    before = [f.model_dump() for f in forecasts]

    simple_average_ensemble(forecasts)

    after = [f.model_dump() for f in forecasts]
    assert before == after


# --- inverse_error_weighted_ensemble ---


def test_inverse_error_weighted_correct_result_verified_manually():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0), _make_forecast(30.0)]
    errors = [1.0, 2.0, 4.0]

    # Manual calculation:
    # inverse errors: 1/1=1, 1/2=0.5, 1/4=0.25 -> sum = 1.75
    # weights: 1/1.75, 0.5/1.75, 0.25/1.75
    # result: 10*(1/1.75) + 20*(0.5/1.75) + 30*(0.25/1.75)
    expected = (1 / 1.75) * 10.0 + (0.5 / 1.75) * 20.0 + (0.25 / 1.75) * 30.0

    uap = inverse_error_weighted_ensemble(forecasts, errors)
    assert uap.result == pytest.approx(expected)
    assert uap.information_class == InformationClass.ESTIMATE


def test_inverse_error_weighted_dependencies_list_every_input_id():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0)]
    errors = [1.0, 2.0]
    uap = inverse_error_weighted_ensemble(forecasts, errors)
    assert set(uap.dependencies) == {f.id for f in forecasts}


def test_inverse_error_weighted_disagreement_set_ref_matches_inputs():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0)]
    errors = [1.0, 2.0]
    uap = inverse_error_weighted_ensemble(forecasts, errors)
    assert uap.disagreement_set_ref == DISAGREEMENT_SET_REF


def test_inverse_error_weighted_raises_on_mismatched_subject():
    mismatched = _make_forecast(20.0)
    mismatched.subject = "a different subject"
    with pytest.raises(ValueError):
        inverse_error_weighted_ensemble([_make_forecast(10.0), mismatched], [1.0, 2.0])


def test_inverse_error_weighted_raises_when_disagreement_set_ref_not_shared():
    other_ref = _make_forecast(20.0)
    other_ref.disagreement_set_ref = "a-different-set"
    with pytest.raises(ValueError):
        inverse_error_weighted_ensemble([_make_forecast(10.0), other_ref], [1.0, 2.0])


def test_inverse_error_weighted_raises_on_length_mismatch():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0)]
    with pytest.raises(ValueError):
        inverse_error_weighted_ensemble(forecasts, [1.0])


def test_inverse_error_weighted_raises_on_zero_error():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0)]
    with pytest.raises(ValueError):
        inverse_error_weighted_ensemble(forecasts, [1.0, 0.0])


def test_inverse_error_weighted_raises_on_near_zero_error():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0)]
    with pytest.raises(ValueError):
        inverse_error_weighted_ensemble(forecasts, [1.0, 1e-12])


def test_inverse_error_weighted_raises_on_negative_error():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0)]
    with pytest.raises(ValueError):
        inverse_error_weighted_ensemble(forecasts, [1.0, -0.5])


def test_inverse_error_weighted_does_not_mutate_inputs():
    forecasts = [_make_forecast(10.0), _make_forecast(20.0), _make_forecast(30.0)]
    errors = [1.0, 2.0, 4.0]
    before = [f.model_dump() for f in forecasts]

    inverse_error_weighted_ensemble(forecasts, errors)

    after = [f.model_dump() for f in forecasts]
    assert before == after


# --- confidence responds to spread ---


def test_confidence_is_higher_for_clustered_than_spread_inputs():
    clustered = [_make_forecast(0.30), _make_forecast(0.31), _make_forecast(0.32)]
    spread = [_make_forecast(0.10), _make_forecast(0.50), _make_forecast(0.90)]

    clustered_uap = simple_average_ensemble(clustered)
    spread_uap = simple_average_ensemble(spread)

    assert clustered_uap.confidence == ConfidenceLevel.HIGH
    assert spread_uap.confidence == ConfidenceLevel.LOW
    assert clustered_uap.confidence != spread_uap.confidence


def test_confidence_is_higher_for_clustered_than_spread_inputs_inverse_error_weighted():
    clustered = [_make_forecast(0.30), _make_forecast(0.31), _make_forecast(0.32)]
    spread = [_make_forecast(0.10), _make_forecast(0.50), _make_forecast(0.90)]
    errors = [0.05, 0.08, 0.03]

    clustered_uap = inverse_error_weighted_ensemble(clustered, errors)
    spread_uap = inverse_error_weighted_ensemble(spread, errors)

    assert clustered_uap.confidence == ConfidenceLevel.HIGH
    assert spread_uap.confidence == ConfidenceLevel.LOW
