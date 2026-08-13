"""
Stage 2 — Validation & Normalisation (Phase E2;
`ENGINE_PIPELINE_SPECIFICATION.md` Stage 2): "check raw data for
structural validity, staleness, duplication, and schema conformance;
normalise units and formats. Data failing checks is quarantined and
flagged — never silently corrected or discarded without a record."

Every function here is STATELESS and operates on one `RawPayload` at a
time (plus, where a check genuinely needs it, an explicit "previous
value" passed in by the caller) — no function here maintains its own
memory of what it has already seen. Duplicate detection specifically
needs cross-call state (has this exact observation already been
ingested?), so it deliberately lives in `ingestion.py`'s orchestration
layer instead, alongside the cache it naturally uses for that purpose,
not here.

Every check returns its finding as a `FailureResult` (never raises) —
Stage 2's own job is to CLASSIFY and QUARANTINE bad data, not abort the
whole ingestion run over one bad record. A record with zero issues
becomes the corresponding canonical payload (`MarketObservation` /
`MacroObservation` / `StructuredEvent`, `shared/optifi_shared/payloads.py`);
a record with any issues becomes `(None, [FailureResult, ...])` instead
— ALL issues found are returned together, not just the first, matching
this project's established verification pattern
(`verify_optimisation_candidate`, VERIFICATION_FRAMEWORK.md Section 5.5).

Known, explicitly acknowledged scope limits (not silently pretended
away):
- Calendar-mismatch checking is a bare weekend check, not a real
  exchange holiday calendar (which varies per exchange and is a
  separate, larger undertaking).
- Discontinuity detection cannot currently distinguish a genuine data
  error from an unhandled corporate action (e.g. a stock split) — a
  flagged discontinuity's message says so explicitly rather than
  claiming false precision.
- "Impossible value" range checks are only applied where a universal
  rule genuinely exists (a market price can never be <= 0); macro
  indicators are checked only for basic well-formedness (finite,
  non-NaN), since a legitimate macro value's plausible range is
  indicator-specific and not something this module assumes.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from optifi_shared import (
    CalendarMismatchFailure,
    CurrencyMismatchFailure,
    DiscontinuityFailure,
    FailureResult,
    ImpossibleValueFailure,
    MacroObservation,
    MarketObservation,
    StaleInputFailure,
    StructuredEvent,
    TimestampInconsistencyFailure,
)

from .providers import RawPayload

# DESIGNED calibration placeholders (consistent with this project's
# established pattern of naming and justifying such constants rather
# than leaving them as unexplained magic numbers — e.g.
# verification-engine's own _LOSS_CAP_PROXIMITY_THRESHOLD): a single-step
# move exceeding 50% of the prior value is flagged as a discontinuity.
# Chosen as a round, deliberately generous threshold -- wide enough that
# genuine, if unusual, single-day market moves don't trigger false
# positives, narrow enough to catch a plausible fat-fingered/decimal-
# point data error. Real calibration against real market data is a
# later, empirical step, not performed here.
_DISCONTINUITY_THRESHOLD_FRACTION = 0.5


def _failure(category_cls: type, message: str) -> FailureResult:
    return FailureResult(category=category_cls.category, message=message)


def _check_timestamp_consistency(raw: RawPayload, observation_time: datetime) -> FailureResult | None:
    retrieved_at = raw.retrieved_at
    if retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
    if observation_time.tzinfo is None:
        observation_time = observation_time.replace(tzinfo=timezone.utc)
    if retrieved_at < observation_time:
        return _failure(
            TimestampInconsistencyFailure,
            f"retrieved_at ({retrieved_at!r}) is before observation_time "
            f"({observation_time!r}) — data cannot have been retrieved "
            "before it was observed.",
        )
    return None


def _check_staleness(observation_time: datetime, now: datetime, staleness_threshold: timedelta) -> FailureResult | None:
    if observation_time.tzinfo is None:
        observation_time = observation_time.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    age = now - observation_time
    if age > staleness_threshold:
        return _failure(
            StaleInputFailure,
            f"observation_time ({observation_time!r}) is {age} old, "
            f"exceeding the staleness threshold ({staleness_threshold}).",
        )
    return None


def _check_weekend_calendar_mismatch(observation_time: datetime) -> FailureResult | None:
    # weekday(): Monday=0 ... Sunday=6. A bare weekend check, NOT a real
    # exchange holiday calendar — see module docstring.
    if observation_time.weekday() >= 5:
        return _failure(
            CalendarMismatchFailure,
            f"observation_time ({observation_time!r}) falls on a "
            "weekend — markets are not open. This check only catches "
            "weekends, not exchange-specific holidays.",
        )
    return None


def validate_market_observation(
    raw: RawPayload,
    expected_currency: str,
    now: datetime,
    staleness_threshold: timedelta,
    previous_price: float | None = None,
) -> tuple[MarketObservation | None, list[FailureResult]]:
    """Stage 2 checks for a single Category A (market) raw record."""
    issues: list[FailureResult] = []
    data = raw.raw_data

    instrument_id = data.get("instrument_id")
    price = data.get("price")
    currency = data.get("currency")
    observation_time_raw = data.get("observation_time")

    if instrument_id is None:
        issues.append(_failure(ImpossibleValueFailure, "market observation is missing 'instrument_id'"))
    if observation_time_raw is None:
        issues.append(_failure(ImpossibleValueFailure, "market observation is missing 'observation_time'"))
        observation_time = None
    else:
        observation_time = datetime.fromisoformat(observation_time_raw)

    if price is None:
        issues.append(_failure(ImpossibleValueFailure, "market observation is missing 'price'"))
    elif not math.isfinite(price) or price <= 0:
        issues.append(
            _failure(ImpossibleValueFailure, f"market price must be a positive, finite number; got {price!r}")
        )

    if currency is None:
        issues.append(_failure(CurrencyMismatchFailure, "market observation is missing 'currency'"))
    elif currency != expected_currency:
        issues.append(
            _failure(
                CurrencyMismatchFailure,
                f"expected currency {expected_currency!r}, got {currency!r} — "
                "refusing to silently mix scales.",
            )
        )

    if observation_time is not None:
        timestamp_issue = _check_timestamp_consistency(raw, observation_time)
        if timestamp_issue is not None:
            issues.append(timestamp_issue)

        staleness_issue = _check_staleness(observation_time, now, staleness_threshold)
        if staleness_issue is not None:
            issues.append(staleness_issue)

        calendar_issue = _check_weekend_calendar_mismatch(observation_time)
        if calendar_issue is not None:
            issues.append(calendar_issue)

    if price is not None and math.isfinite(price) and previous_price is not None and previous_price != 0:
        relative_move = abs(price - previous_price) / abs(previous_price)
        if relative_move > _DISCONTINUITY_THRESHOLD_FRACTION:
            issues.append(
                _failure(
                    DiscontinuityFailure,
                    f"price moved {relative_move:.0%} from the previous "
                    f"observation ({previous_price!r} -> {price!r}), "
                    f"exceeding the {_DISCONTINUITY_THRESHOLD_FRACTION:.0%} "
                    "threshold. This could be a genuine data error, or an "
                    "unhandled corporate action (e.g. a stock split) this "
                    "check cannot currently distinguish from one.",
                )
            )

    if issues:
        return None, issues

    return MarketObservation(instrument_id=instrument_id, price=price, currency=currency), []


def validate_macro_observation(
    raw: RawPayload,
    now: datetime,
    staleness_threshold: timedelta,
) -> tuple[MacroObservation | None, list[FailureResult]]:
    """Stage 2 checks for a single Category B (macro) raw record."""
    issues: list[FailureResult] = []
    data = raw.raw_data

    indicator_name = data.get("indicator_name")
    value = data.get("value")
    unit = data.get("unit")
    observation_time_raw = data.get("observation_time")

    if indicator_name is None:
        issues.append(_failure(ImpossibleValueFailure, "macro observation is missing 'indicator_name'"))
    if observation_time_raw is None:
        issues.append(_failure(ImpossibleValueFailure, "macro observation is missing 'observation_time'"))
        observation_time = None
    else:
        observation_time = datetime.fromisoformat(observation_time_raw)

    if value is None:
        issues.append(_failure(ImpossibleValueFailure, "macro observation is missing 'value'"))
    elif not math.isfinite(value):
        # No universal plausible-range check (a macro indicator's valid
        # range is indicator-specific) -- only basic well-formedness.
        issues.append(_failure(ImpossibleValueFailure, f"macro value must be finite; got {value!r}"))

    if observation_time is not None:
        timestamp_issue = _check_timestamp_consistency(raw, observation_time)
        if timestamp_issue is not None:
            issues.append(timestamp_issue)
        staleness_issue = _check_staleness(observation_time, now, staleness_threshold)
        if staleness_issue is not None:
            issues.append(staleness_issue)

    if issues:
        return None, issues

    return MacroObservation(indicator_name=indicator_name, value=value, unit=unit), []


def validate_structured_event(raw: RawPayload) -> tuple[StructuredEvent | None, list[FailureResult]]:
    """Stage 2 checks for a single Category D/E (event) raw record."""
    issues: list[FailureResult] = []
    data = raw.raw_data

    event_type = data.get("event_type")
    description = data.get("description")
    entity_ids = data.get("entity_ids", [])
    observation_time_raw = data.get("observation_time")

    if event_type is None:
        issues.append(_failure(ImpossibleValueFailure, "structured event is missing 'event_type'"))
    if description is None:
        issues.append(_failure(ImpossibleValueFailure, "structured event is missing 'description'"))

    if observation_time_raw is not None:
        observation_time = datetime.fromisoformat(observation_time_raw)
        timestamp_issue = _check_timestamp_consistency(raw, observation_time)
        if timestamp_issue is not None:
            issues.append(timestamp_issue)

    if issues:
        return None, issues

    return StructuredEvent(event_type=event_type, description=description, entity_ids=entity_ids), []
