"""
TransmissionGraph — PHASE E4 brief, Part 2: "Use the causal layer to
represent supported economic pathways... Each link must retain: evidence;
direction; lag; uncertainty; regime dependency."

A graph whose edges are real `CausalClaim` objects (`causal_claim.py`) —
not a new, parallel representation of causal relationships. Every edge
already carries evidence (`mechanism`/`historical_precedent`, enforced at
`CausalClaim` construction), direction (`cause_entity_id` ->
`effect_entity_id`), lag (`time_lag`), uncertainty (`confidence`), and
regime dependency (`regime`, added this phase) — this module's own job is
purely the graph structure (indexing, traversal, multi-hop pathway
discovery) on top of edges that already satisfy
CAUSAL_ENGINE_SPEC.md Section 5 by construction.

This module does not choose or implement a causal-inference methodology
(CAUSAL_ENGINE_SPEC.md Section 3 remains exactly as undecided) — it is
pure graph plumbing over whatever `CausalClaim`s a caller has already
constructed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from optifi_shared import UnsupportedFailure

from .causal_claim import CausalClaim

# A "limited initial scenario library... not hundreds of scenarios"
# (Part 6) implies a correspondingly small transmission graph — this
# depth cap is a safety bound against runaway path enumeration on a
# graph that should, by design, stay small, not a claim that real
# economic transmission never exceeds 6 hops.
DEFAULT_MAX_DEPTH = 6


@dataclass(frozen=True)
class Pathway:
    """One directed chain of `CausalClaim` edges from a starting entity
    to an ending entity — `edges[i].effect_entity_id ==
    edges[i + 1].cause_entity_id` for every consecutive pair."""

    edges: tuple[CausalClaim, ...]

    @property
    def start_entity_id(self) -> str:
        return self.edges[0].cause_entity_id

    @property
    def end_entity_id(self) -> str:
        return self.edges[-1].effect_entity_id

    @property
    def entity_ids(self) -> tuple[str, ...]:
        """Every entity visited, in order, including start and end."""
        return (self.start_entity_id, *(edge.effect_entity_id for edge in self.edges))


class TransmissionGraph:
    """
    A directed multigraph of `CausalClaim` edges. "Multi" matters:
    `causal-engine`'s own multi-model-disagreement rule
    (CAUSAL_ENGINE_SPEC.md Section 7) means two competing claims can
    legitimately share the same `(cause_entity_id, effect_entity_id)`
    pair — both are kept, never silently collapsed into one.
    """

    def __init__(self) -> None:
        self._edges_by_cause: dict[str, list[CausalClaim]] = {}

    def add_edge(self, claim: CausalClaim) -> None:
        self._edges_by_cause.setdefault(claim.cause_entity_id, []).append(claim)

    def add_edges(self, claims: list[CausalClaim]) -> None:
        for claim in claims:
            self.add_edge(claim)

    def edges_from(self, entity_id: str) -> list[CausalClaim]:
        """Every direct outgoing edge from `entity_id` — empty if none
        registered (not an error; a caller asking 'what does X affect'
        legitimately may get no answer)."""
        return list(self._edges_by_cause.get(entity_id, []))

    def edges_between(self, cause_entity_id: str, effect_entity_id: str) -> list[CausalClaim]:
        """Every direct edge cause -> effect — plural when competing
        claims disagree about the same relationship (Section 7)."""
        return [e for e in self.edges_from(cause_entity_id) if e.effect_entity_id == effect_entity_id]

    def find_pathways(
        self, start_entity_id: str, end_entity_id: str, max_depth: int = DEFAULT_MAX_DEPTH
    ) -> list[Pathway]:
        """
        Every distinct directed pathway from `start_entity_id` to
        `end_entity_id`, up to `max_depth` hops. Explores every
        combination across competing edges at each hop (multi-model
        disagreement means more than one path can share the same entity
        sequence with different evidence/magnitude behind each hop) and
        never revisits an entity within one path (cycle-safe by
        construction, not by an added check). Returns an empty list —
        not an error — when no pathway exists; `require_pathway` below is
        the hard-failure counterpart for callers that need one to exist.
        """
        results: list[Pathway] = []

        def _walk(current_entity: str, path_so_far: tuple[CausalClaim, ...], visited: frozenset[str]) -> None:
            if current_entity == end_entity_id and path_so_far:
                results.append(Pathway(edges=path_so_far))
                # A pathway ending here can still continue further (a
                # longer path might also legitimately reach end_entity_id
                # again only if the graph re-enters it, which `visited`
                # already forbids) — no early return needed beyond that.
            if len(path_so_far) >= max_depth:
                return
            for edge in self.edges_from(current_entity):
                if edge.effect_entity_id in visited:
                    continue  # cycle guard
                _walk(edge.effect_entity_id, path_so_far + (edge,), visited | {edge.effect_entity_id})

        _walk(start_entity_id, (), frozenset({start_entity_id}))
        return results

    def require_pathway(
        self, start_entity_id: str, end_entity_id: str, max_depth: int = DEFAULT_MAX_DEPTH
    ) -> list[Pathway]:
        """
        Testing Requirement: "unsupported causal edge" — the hard-failure
        counterpart to `find_pathways`. Raises `UnsupportedFailure`
        rather than letting a caller silently proceed as if a
        transmission mechanism existed when none does; never fabricates
        a plausible-looking pathway to fill the gap.
        """
        pathways = self.find_pathways(start_entity_id, end_entity_id, max_depth)
        if not pathways:
            raise UnsupportedFailure(
                f"require_pathway: no supported causal pathway from "
                f"{start_entity_id!r} to {end_entity_id!r} exists in this "
                f"transmission graph (searched up to depth {max_depth}) — "
                "this project never fabricates a transmission mechanism "
                "that hasn't been registered as evidenced CausalClaim "
                "edges."
            )
        return pathways
