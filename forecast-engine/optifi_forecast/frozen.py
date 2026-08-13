"""
Frozen forecasts — PHASE E3 brief, Part I: "Forecasts must become
immutable historical predictions. If a model changes tomorrow,
yesterday's forecast must remain exactly as it was."

`UAP` objects are never mutated in place anywhere in this project (Phase
E1's `supersede()` established the "return new objects" discipline this
module reuses directly rather than inventing a second mechanism) — a
forecast UAP is already immutable the moment it is constructed, the same
way every other UAP is. What Part I actually needs on top of that is a
DELIBERATE, validated path for "a new model version supersedes an old
forecast for the same subject" — that is genuinely a revision, not a
mutation, and `new_forecast_supersedes_old` below is that path.
"""

from __future__ import annotations

from optifi_shared import InformationClass, supersede, UAP


def new_forecast_supersedes_old(old_forecast: UAP, new_forecast: UAP) -> tuple[UAP, UAP]:
    """
    Thin, forecast-specific wrapper over `shared.supersede()`: same
    return shape `(new_with_supersedes_linked, old_marked_superseded)`,
    with two additional checks specific to forecasts that `supersede()`
    itself (being generic to every UAP kind) does not make:

    - both inputs must be `information_class=ESTIMATE` (a forecast is
      always an ESTIMATE — Section 6 of `FORECAST_ENGINE_SPEC.md`);
    - `new_forecast.producer` must differ from `old_forecast.producer`
      — this project's existing convention embeds model identity/version
      in `producer` (e.g. "forecast-engine / econometric-ses v2"), so an
      unchanged `producer` means this isn't actually a model version
      change, and calling this function would misrepresent a same-model
      re-run as a genuine revision.

    `old_forecast` itself is returned completely untouched in
    `old_marked_superseded`'s SOURCE — i.e. the caller's original
    `old_forecast` reference is never modified, exactly as
    `supersede()` already guarantees; this wrapper adds no new
    mutation risk.
    """
    if old_forecast.information_class != InformationClass.ESTIMATE or new_forecast.information_class != InformationClass.ESTIMATE:
        raise ValueError(
            "new_forecast_supersedes_old: both old_forecast and new_forecast "
            "must be information_class=ESTIMATE — a forecast is always an "
            "ESTIMATE (FORECAST_ENGINE_SPEC.md Section 6)."
        )
    if old_forecast.producer == new_forecast.producer:
        raise ValueError(
            "new_forecast_supersedes_old: old_forecast.producer == "
            f"new_forecast.producer ({old_forecast.producer!r}) — this project's "
            "convention embeds model identity/version in `producer`, so an "
            "unchanged producer means this is not a genuine model version "
            "change. Use supersede() directly if a same-model re-run for "
            "revised input data is genuinely intended instead."
        )
    return supersede(old_forecast, new_forecast)
