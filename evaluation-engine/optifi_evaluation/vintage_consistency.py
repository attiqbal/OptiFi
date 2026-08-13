"""
Vintage-consistency check — Testing Requirements: "revised macro data."

A forecast conditioned on a macro release's advance estimate is not
retroactively wrong when that release is later revised (`supersede()`,
`data-engine/optifi_data/ingestion.py`'s `ingest_macro_observation`) — but
evaluating it as if nothing changed would be dishonest. This module
detects the mismatch and surfaces it as an explicit caveat, rather than
either (a) silently re-scoring the old forecast against the revised value
as though the forecast had known it, or (b) silently treating the
forecast as still fully current.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VintageStatus = Literal["CURRENT", "STALE_VINTAGE", "UNVERIFIABLE"]


@dataclass(frozen=True)
class VintageCheckResult:
    status: VintageStatus
    message: str


def check_vintage_consistency(
    forecast_data_vintage: str | None, current_data_vintage: str | None
) -> VintageCheckResult:
    """
    `forecast_data_vintage`: `ForecastRecord.data_vintage` — the vintage
    the forecast was actually conditioned on. `current_data_vintage`: the
    vintage now on record for that same underlying subject (post any
    `supersede()` revisions since the forecast was made).
    """
    if forecast_data_vintage is None or current_data_vintage is None:
        return VintageCheckResult(
            status="UNVERIFIABLE",
            message="data_vintage not recorded on one or both sides — cannot confirm vintage consistency.",
        )
    if forecast_data_vintage == current_data_vintage:
        return VintageCheckResult(status="CURRENT", message="forecast's input vintage matches the current vintage.")
    return VintageCheckResult(
        status="STALE_VINTAGE",
        message=(
            f"forecast was conditioned on vintage {forecast_data_vintage!r}, but "
            f"the underlying data has since been revised to {current_data_vintage!r} "
            "(supersede()) — evaluate this forecast's accuracy with that caveat "
            "attached; do not silently re-score it against the revised value as "
            "though it had been available at forecast time."
        ),
    )
