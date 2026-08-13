"""
Part I frozen forecasts — Testing Requirements: "model version change,"
"immutable historical prediction."
"""

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_forecast import new_forecast_supersedes_old

SUBJECT = "test target"


def _forecast(result: float, producer: str) -> UAP:
    return UAP(
        subject=SUBJECT,
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="test",
        producer=producer,
        confidence=ConfidenceLevel.MODERATE,
    )


def test_model_version_change_supersedes_and_preserves_the_old_forecast_exactly():
    old = _forecast(10.0, "forecast-engine / econometric-ses v1")
    old_snapshot = old.model_dump()

    new = _forecast(12.0, "forecast-engine / econometric-ses v2")
    new_linked, old_superseded = new_forecast_supersedes_old(old, new)

    # "If a model changes tomorrow, yesterday's forecast must remain
    # exactly as it was" — the ORIGINAL object, held by whoever still
    # references it, is untouched.
    assert old.model_dump() == old_snapshot
    assert old.result == 10.0
    assert old.validation_status == ValidationStatus.PROVISIONAL

    # The returned superseded copy is distinctly marked, the original is not.
    assert old_superseded.validation_status == ValidationStatus.SUPERSEDED
    assert old_superseded.result == 10.0  # value itself never changes, only status
    assert new_linked.result == 12.0
    assert old.id in new_linked.supersedes


def test_unchanged_producer_is_rejected_as_not_a_genuine_version_change():
    old = _forecast(10.0, "forecast-engine / econometric-ses v1")
    same_model_rerun = _forecast(10.5, "forecast-engine / econometric-ses v1")
    with pytest.raises(ValueError):
        new_forecast_supersedes_old(old, same_model_rerun)


def test_non_estimate_forecast_is_rejected():
    old = _forecast(10.0, "forecast-engine / econometric-ses v1")
    not_a_forecast = old.model_copy(update={"information_class": InformationClass.FACT})
    new = _forecast(12.0, "forecast-engine / econometric-ses v2")
    with pytest.raises(ValueError):
        new_forecast_supersedes_old(not_a_forecast, new)
