"""
ForecastRecord — the Stage 14 unit of work (FORECAST_ENGINE_SPEC.md
Section 7; PHASE E3 brief, Part E/I).

Tracks exactly the fields the brief names: forecast packet, target,
forecast timestamp, horizon, predicted distribution/estimate, realised
outcome, error, calibration, regime, model version, data vintage.

**Immutability (Part I — "Frozen Forecasts")**: a `ForecastRecord` is a
frozen pydantic model. Once constructed, none of its fields — including
the prediction itself — can be reassigned; `record.predicted_point = 5.0`
raises. "If a model changes tomorrow, yesterday's forecast must remain
exactly as it was" is enforced structurally, not by convention: there is
no setter to accidentally call.

A realised outcome, by definition, is not known at forecast time — it
arrives later. Rather than allow a mutation for that one field (which
would reopen exactly the door frozen=True closes), `record_outcome()`
returns a **new** `ForecastRecord` with the outcome/error/calibration
fields populated, leaving the original object — and anyone still holding
a reference to it — completely untouched. This mirrors `supersede()`'s
own "return new objects, never mutate inputs" discipline
(`shared/optifi_shared/uap.py`), applied here to outcome-recording rather
than revision.

A forecast is one of exactly four shapes, matching the brief's own
Evaluation Metrics categories (Part E) — a record sets exactly the fields
relevant to its `forecast_kind` and leaves the others `None`, so a metric
function can dispatch on which fields are actually populated rather than
guessing from `forecast_kind` alone:

- **POINT**: `predicted_point` (+ optional `predicted_lower`/`predicted_upper`
  for an interval forecast layered on top of a point estimate).
- **PROBABILITY**: `predicted_distribution` — a mapping of outcome-bucket
  label to probability, summing to ~1.0 (e.g. {"falls": 0.2, "flat": 0.5,
  "rises": 0.3}), matching PRODUCT_VISION.md's own bucketed-probability
  forecasting style already cited in FORECAST_ENGINE_SPEC.md Section 8.
- **DIRECTION**: `predicted_class` — a discrete label (e.g. "up"/"down").
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ForecastKind(str, Enum):
    """Which of the four evaluation-metric categories (Part E) this
    forecast belongs to. Determines which metrics.py functions apply —
    "use target-appropriate metrics... not one blanket set."""

    POINT = "POINT"
    INTERVAL = "INTERVAL"
    PROBABILITY = "PROBABILITY"
    DIRECTION = "DIRECTION"


class ForecastRecord(BaseModel):
    """
    One immutable historical prediction. See module docstring for the
    immutability discipline and the four forecast shapes.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))

    # --- What this forecasts (Part E's required tracked fields) ---
    forecast_packet_id: str = Field(
        ..., description="The id of the forecast-engine UAP this record tracks."
    )
    target: str = Field(..., description="Stable target identifier, e.g. 'UK CPI YoY, 3-month horizon'.")
    forecast_timestamp: datetime = Field(
        ..., description="When the forecast was made (the UAP's own as_of/generated_at)."
    )
    horizon: str = Field(..., description="e.g. '3-month', '1-month', '1-quarter'.")
    forecast_kind: ForecastKind

    # --- The prediction itself — exactly one shape's fields populated ---
    predicted_point: float | None = None
    predicted_lower: float | None = None
    predicted_upper: float | None = None
    predicted_distribution: dict[str, float] | None = None
    predicted_class: str | None = None

    # --- Model identity (Part H — scorecard join key) ---
    model_id: str = Field(..., description="e.g. 'econometric-ses', 'ml-linear-features', 'baseline-ar1'.")
    model_version: str = Field(..., description="A version string this exact prediction was produced with.")
    data_vintage: str | None = Field(
        default=None,
        description=(
            "The vintage label (UAP.vintage) of the input data this forecast "
            "was fit/conditioned on, e.g. 'second estimate' for a CPI "
            "forecast — used by vintage_consistency.py to detect when the "
            "underlying data has since been revised out from under this "
            "forecast."
        ),
    )
    regime: str | None = Field(
        default=None, description="Free-text market/macro regime label in effect at forecast time, if known."
    )

    # --- Realised outcome — populated only via record_outcome(), never
    # --- set at construction alongside a fresh prediction. ---
    realised_outcome: Any = Field(default=None, description="float for POINT/INTERVAL, str class label for DIRECTION, or a realised-bucket label for PROBABILITY.")
    realised_at: datetime | None = None
    error: float | None = Field(
        default=None, description="Signed error (predicted - realised) for POINT/INTERVAL; None otherwise."
    )

    @model_validator(mode="after")
    def _kind_matches_populated_fields(self) -> "ForecastRecord":
        kind = self.forecast_kind
        if kind == ForecastKind.POINT and self.predicted_point is None:
            raise ValueError("ForecastRecord: forecast_kind=POINT requires predicted_point.")
        if kind == ForecastKind.INTERVAL and (
            self.predicted_point is None or self.predicted_lower is None or self.predicted_upper is None
        ):
            raise ValueError(
                "ForecastRecord: forecast_kind=INTERVAL requires predicted_point, "
                "predicted_lower, and predicted_upper."
            )
        if kind == ForecastKind.PROBABILITY:
            if not self.predicted_distribution:
                raise ValueError("ForecastRecord: forecast_kind=PROBABILITY requires predicted_distribution.")
            total = sum(self.predicted_distribution.values())
            if not (0.99 <= total <= 1.01):
                raise ValueError(
                    f"ForecastRecord: predicted_distribution must sum to ~1.0, got {total!r}."
                )
        if kind == ForecastKind.DIRECTION and self.predicted_class is None:
            raise ValueError("ForecastRecord: forecast_kind=DIRECTION requires predicted_class.")
        return self

    def is_evaluable(self) -> bool:
        """False until a realised outcome has been recorded — the
        "missing realised outcome" case (Testing Requirements): a
        forecast whose horizon hasn't elapsed yet is a normal, expected
        state, not a failure."""
        return self.realised_outcome is not None

    def record_outcome(self, realised_outcome: Any, realised_at: datetime | None = None) -> "ForecastRecord":
        """
        Returns a NEW `ForecastRecord` with the outcome recorded — the
        original is never mutated (see module docstring). Computes
        `error` for POINT/INTERVAL kinds (signed: predicted - realised);
        left `None` for PROBABILITY/DIRECTION, whose "error" is only
        meaningful as a calibration/accuracy metric across many records,
        not a single scalar on one record (metrics.py owns that).
        """
        realised_at = realised_at or datetime.now(timezone.utc)
        error = None
        if self.forecast_kind in (ForecastKind.POINT, ForecastKind.INTERVAL):
            error = self.predicted_point - float(realised_outcome)
        return self.model_copy(
            update={
                "realised_outcome": realised_outcome,
                "realised_at": realised_at,
                "error": error,
            }
        )
