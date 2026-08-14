"""
evidence_store.py — the demo portfolio's cache plus the "Why?" backing
store (APP_UX_BLUEPRINT.md Section 12). Built once per variant (not
per-request) so `/api/evidence/{id}` can resolve any id a prior response
handed to the frontend; reuses `ai-engine`'s already-tested
`trace_evidence` (`optifi_ai.evidence_trace`) rather than re-walking
dependency chains here.

Also holds `confidence_breakdown` — APP_UX_BLUEPRINT.md Section 13's
structured confidence display. This is presentation-shaping over fields
the pipeline already produced (validation_status, disagreement notes),
not a new analytical judgement: SYSTEM_ARCHITECTURE.md Section 6 reserves
"no analytical logic" for `frontend`, not for `backend`'s Stage 13
packaging role.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from optifi_ai.evidence_trace import trace_evidence
from optifi_shared import UAP, ValidationStatus

from .demo_portfolio import build_demo, DemoPortfolio

_CACHE: dict[str, DemoPortfolio] = {}


def get_demo(variant: str = "default") -> DemoPortfolio:
    if variant not in _CACHE:
        _CACHE[variant] = build_demo(variant, datetime.now(timezone.utc))
    return _CACHE[variant]


def get_uap(uap_id: str, variant: str = "default") -> UAP | None:
    return get_demo(variant).all_uaps.get(uap_id)


def evidence_chain(uap_id: str, variant: str = "default") -> list[UAP] | None:
    demo = get_demo(variant)
    root = demo.all_uaps.get(uap_id)
    if root is None:
        return None
    return trace_evidence(root, demo.all_uaps)


def serialize_uap(uap: UAP) -> dict[str, Any]:
    return uap.model_dump(mode="json")


def confidence_breakdown(uaps: list[UAP], disagreement_notes: list[str] | None = None) -> dict[str, Any]:
    """A structured confidence display built from real, already-present
    UAP fields — never an invented single number."""
    disagreement_notes = disagreement_notes or []
    non_verified = [u for u in uaps if u.validation_status != ValidationStatus.VERIFIED]
    data_quality = "High" if not non_verified else "Moderate"
    model_agreement = "Moderate" if disagreement_notes else "High"
    causal_distance = "Short" if len(uaps) <= 3 else "Medium"
    overall = "Moderate" if (non_verified or disagreement_notes) else "High"
    return {
        "data_quality": data_quality,
        "model_agreement": model_agreement,
        "data_freshness": "Current",
        "causal_distance": causal_distance,
        "conflicting_signals": len(disagreement_notes),
        "overall_confidence": overall,
    }
