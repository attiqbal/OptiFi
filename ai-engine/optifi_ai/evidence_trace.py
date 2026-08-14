"""
trace_evidence — the "Why?" pathway (Phase E6 brief: "Every material
conclusion should support a 'Why?' pathway back to underlying analytical
packets"; APP_UX_BLUEPRINT.md Section 12).

Reuses `disclosure.py`'s already-tested dependency/provenance walk
(`_walk_all_dependencies`) rather than re-implementing traversal a second
time — that function is exercised directly by name in
`tests/test_disclosure.py` (diamond-shaped graphs, unresolved references,
duplicate start ids), so it stays defined there; this module only adds a
public, purpose-named entry point for the same real traversal.
"""

from __future__ import annotations

from optifi_shared import UAP

from .disclosure import _walk_all_dependencies


def trace_evidence(uap: UAP, known_uaps: dict[str, UAP] | None = None) -> list[UAP]:
    """Every UAP reachable from `uap` via `dependencies`/`provenance_chain`,
    including `uap` itself. `known_uaps` resolves ids not already directly
    reachable, same convention as `explain_with_disclosure`. A reference
    that cannot be resolved is simply absent from the result — it is the
    caller's job (as in `explain_with_disclosure`) to decide whether an
    unresolved ancestor should be disclosed, not this function's."""
    reachable, _unresolved = _walk_all_dependencies([uap], known_uaps or {})
    return reachable
