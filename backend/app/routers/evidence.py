"""
GET /api/evidence/{id} — the "Why?" drill-down (APP_UX_BLUEPRINT.md
Section 12). Resolves a UAP id to its full dependency/provenance chain via
`ai-engine`'s `trace_evidence`; an id with no resolvable chain (e.g. from
a stale link, or a variant mismatch) returns a structured 404, never a
fabricated chain.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..evidence_store import evidence_chain, serialize_uap

router = APIRouter(tags=["evidence"])


@router.get("/evidence/{uap_id}")
def get_evidence(uap_id: str, portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    chain = evidence_chain(uap_id, portfolio)
    if chain is None:
        raise HTTPException(status_code=404, detail=f"No known analytical packet with id {uap_id!r}.")
    return {"root_id": uap_id, "chain": [serialize_uap(u) for u in chain]}
