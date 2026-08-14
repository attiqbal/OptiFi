"""
Tests for TransmissionGraph — PHASE E4 brief, Part 2, and the required
"unsupported causal edge" adversarial test.
"""

import pytest
from optifi_shared import ConfidenceLevel, UnsupportedFailure, ValidationStatus

from optifi_causal import CausalClaim, TransmissionGraph


def _claim(cause: str, effect: str, mechanism: str = "a plausible mechanism", **overrides) -> CausalClaim:
    defaults = dict(
        subject=f"{cause} -> {effect}",
        validation_status=ValidationStatus.PROVISIONAL,
        result=f"{cause} affects {effect}",
        source="test",
        producer="causal-engine (test)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=cause,
        effect_entity_id=effect,
        mechanism=mechanism,
    )
    defaults.update(overrides)
    return CausalClaim(**defaults)


# --- basic indexing ---


def test_edges_from_returns_direct_outgoing_edges():
    graph = TransmissionGraph()
    edge = _claim("entity:a", "entity:b")
    graph.add_edge(edge)
    assert graph.edges_from("entity:a") == [edge]


def test_edges_from_unknown_entity_returns_empty_not_an_error():
    graph = TransmissionGraph()
    assert graph.edges_from("entity:nowhere") == []


def test_edges_between_returns_multiple_competing_claims():
    """CAUSAL_ENGINE_SPEC.md Section 7: competing claims about the same
    relationship are preserved as a plural set, not collapsed."""
    graph = TransmissionGraph()
    strong = _claim("entity:a", "entity:b", mechanism="a strong-effect mechanism")
    weak = _claim("entity:a", "entity:b", mechanism="a weak-effect mechanism")
    graph.add_edges([strong, weak])
    # UAP/CausalClaim instances aren't hashable (no frozen config), so
    # compare by id rather than putting them in a set.
    result_ids = {edge.id for edge in graph.edges_between("entity:a", "entity:b")}
    assert result_ids == {strong.id, weak.id}


# --- multi-hop pathway discovery ---


def test_find_pathways_single_hop():
    graph = TransmissionGraph()
    edge = _claim("entity:a", "entity:b")
    graph.add_edge(edge)
    pathways = graph.find_pathways("entity:a", "entity:b")
    assert len(pathways) == 1
    assert pathways[0].edges == (edge,)


def test_find_pathways_multi_hop_matches_the_briefs_own_example():
    """Inflation surprise -> policy-rate expectations -> yield curve ->
    duration-sensitive assets (PHASE E4 brief's own worked example)."""
    graph = TransmissionGraph()
    e1 = _claim("entity:inflation-surprise", "entity:policy-rate-expectations")
    e2 = _claim("entity:policy-rate-expectations", "entity:yield-curve")
    e3 = _claim("entity:yield-curve", "entity:duration-sensitive-assets")
    graph.add_edges([e1, e2, e3])

    pathways = graph.find_pathways("entity:inflation-surprise", "entity:duration-sensitive-assets")
    assert len(pathways) == 1
    assert pathways[0].edges == (e1, e2, e3)
    assert pathways[0].entity_ids == (
        "entity:inflation-surprise",
        "entity:policy-rate-expectations",
        "entity:yield-curve",
        "entity:duration-sensitive-assets",
    )


def test_find_pathways_explores_multiple_competing_branches():
    graph = TransmissionGraph()
    via_rates = _claim("entity:a", "entity:mid1", mechanism="via rates")
    via_credit = _claim("entity:a", "entity:mid2", mechanism="via credit")
    to_end_1 = _claim("entity:mid1", "entity:end", mechanism="mid1 to end")
    to_end_2 = _claim("entity:mid2", "entity:end", mechanism="mid2 to end")
    graph.add_edges([via_rates, via_credit, to_end_1, to_end_2])

    pathways = graph.find_pathways("entity:a", "entity:end")
    assert len(pathways) == 2
    entity_id_sequences = {p.entity_ids for p in pathways}
    assert entity_id_sequences == {
        ("entity:a", "entity:mid1", "entity:end"),
        ("entity:a", "entity:mid2", "entity:end"),
    }


def test_find_pathways_never_revisits_an_entity_cycle_safe():
    graph = TransmissionGraph()
    graph.add_edges(
        [
            _claim("entity:a", "entity:b"),
            _claim("entity:b", "entity:a"),  # cycle back
            _claim("entity:b", "entity:c"),
        ]
    )
    pathways = graph.find_pathways("entity:a", "entity:c")
    assert len(pathways) == 1
    assert pathways[0].entity_ids == ("entity:a", "entity:b", "entity:c")


def test_find_pathways_respects_max_depth():
    graph = TransmissionGraph()
    graph.add_edges(
        [
            _claim("entity:a", "entity:b"),
            _claim("entity:b", "entity:c"),
            _claim("entity:c", "entity:d"),
        ]
    )
    assert graph.find_pathways("entity:a", "entity:d", max_depth=2) == []
    assert len(graph.find_pathways("entity:a", "entity:d", max_depth=3)) == 1


def test_find_pathways_no_path_returns_empty_list_not_an_error():
    graph = TransmissionGraph()
    graph.add_edge(_claim("entity:a", "entity:b"))
    assert graph.find_pathways("entity:a", "entity:nowhere") == []


# --- Testing Requirement: "unsupported causal edge" ---


def test_require_pathway_raises_unsupported_failure_when_none_exists():
    graph = TransmissionGraph()
    graph.add_edge(_claim("entity:a", "entity:b"))
    with pytest.raises(UnsupportedFailure):
        graph.require_pathway("entity:a", "entity:completely-unconnected-entity")


def test_require_pathway_returns_pathways_when_they_exist():
    graph = TransmissionGraph()
    edge = _claim("entity:a", "entity:b")
    graph.add_edge(edge)
    pathways = graph.require_pathway("entity:a", "entity:b")
    assert len(pathways) == 1


def test_require_pathway_on_an_entirely_empty_graph_raises():
    graph = TransmissionGraph()
    with pytest.raises(UnsupportedFailure):
        graph.require_pathway("entity:a", "entity:b")
