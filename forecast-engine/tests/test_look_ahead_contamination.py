"""
Testing Requirement: "look-ahead contamination" — a forecast UAP that
declares an `as_of` cutoff must be rejected if it depends on an upstream
record that was not genuinely available by then. Reuses
verification-engine's existing `check_no_look_ahead_contamination`
(Phase E1) directly rather than re-implementing the check here.
"""

from datetime import datetime, timezone

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_verification import check_no_look_ahead_contamination, VerdictType


def _macro_input(publication_time: datetime) -> UAP:
    return UAP(
        subject="macro indicator: SYNTH_CPI",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=2.9,
        source="test statistics office",
        producer="data-engine / fixture-provider",
        confidence=ConfidenceLevel.MODERATE,
        publication_time=publication_time,
        retrieval_time=publication_time,
    )


def _forecast_depending_on(input_uap: UAP, as_of: datetime) -> UAP:
    return UAP(
        subject="UK CPI YoY, 3-month horizon",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=3.0,
        source="computed",
        producer="forecast-engine / econometric-ses v1",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=[input_uap.id],
        as_of=as_of,
    )


def test_forecast_using_data_published_after_its_own_as_of_is_rejected():
    macro_input = _macro_input(publication_time=datetime(2026, 8, 15, tzinfo=timezone.utc))
    forecast = _forecast_depending_on(macro_input, as_of=datetime(2026, 8, 1, tzinfo=timezone.utc))

    verdict = check_no_look_ahead_contamination(forecast, known_packets={macro_input.id: macro_input})

    assert verdict.verdict_type == VerdictType.REJECT
    assert "look-ahead contamination" in verdict.reasons[0]


def test_forecast_using_data_available_before_its_as_of_passes():
    macro_input = _macro_input(publication_time=datetime(2026, 7, 15, tzinfo=timezone.utc))
    forecast = _forecast_depending_on(macro_input, as_of=datetime(2026, 8, 1, tzinfo=timezone.utc))

    verdict = check_no_look_ahead_contamination(forecast, known_packets={macro_input.id: macro_input})

    assert verdict.verdict_type == VerdictType.PASS
