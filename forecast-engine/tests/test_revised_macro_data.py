"""
Testing Requirement: "revised macro data" — the full cross-package
loop: data-engine ingests an advance CPI estimate, then a revision
(Phase E2's own `ingest_macro_observation`/`supersede()` machinery,
unmodified); a forecast made on the advance estimate carries that
vintage in its `ForecastRecord.data_vintage`; evaluation-engine's
`check_vintage_consistency` correctly flags that the forecast's input
has since been revised, without silently re-scoring the forecast as if
the revision had been visible at forecast time.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from optifi_data import FixtureProvider, ingest_macro_observation, ObservationCache
from optifi_evaluation import check_vintage_consistency, ForecastKind, ForecastRecord

FIXTURE_DIR = Path(__file__).parent.parent.parent / "data-engine" / "optifi_data" / "fixtures"
NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def test_forecast_on_advance_estimate_is_flagged_after_revision(tmp_path):
    provider = FixtureProvider(FIXTURE_DIR)
    cache = ObservationCache(tmp_path / "cache")

    advance_time = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
    advance = ingest_macro_observation(
        provider, cache, "SYNTH_CPI", now=NOW, staleness_threshold=timedelta(days=60), as_of=advance_time
    )
    assert advance.uap.vintage == "advance estimate"

    forecast = ForecastRecord(
        forecast_packet_id="forecast-1",
        target="UK CPI YoY, 3-month horizon",
        forecast_timestamp=advance_time,
        horizon="3-month",
        forecast_kind=ForecastKind.POINT,
        predicted_point=3.0,
        model_id="econometric-ses",
        model_version="v1",
        data_vintage=advance.uap.vintage,
    )

    # Before any revision, the forecast's vintage matches what's on record.
    assert check_vintage_consistency(forecast.data_vintage, advance.uap.vintage).status == "CURRENT"

    revised = ingest_macro_observation(
        provider, cache, "SYNTH_CPI", now=NOW, staleness_threshold=timedelta(days=60), previous_uap=advance.uap
    )
    assert revised.uap.vintage == "second estimate"
    assert revised.uap.result.value != advance.uap.result.value

    # After the revision, the SAME forecast object's recorded vintage is
    # now stale relative to what data-engine currently has on record —
    # detected, not silently ignored.
    result = check_vintage_consistency(forecast.data_vintage, revised.uap.vintage)
    assert result.status == "STALE_VINTAGE"

    # The forecast itself was never mutated by any of this.
    assert forecast.data_vintage == "advance estimate"
