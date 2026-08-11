"""
Tests for explain_with_disclosure (Stage 13, AI_ENGINE_SPEC.md Section
3.4; Never-list item 9: never present a non-VERIFIED item without
flagging its validation_status).
"""

from typing import Any

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_ai import StubExplanationGenerator, explain_with_disclosure


class SilentOnStatusGenerator:
    """A cooperative generator whose text never mentions validation status
    at all — proves the disclosure comes from code, not the generator."""

    def generate(self, prompt: str, context: dict[str, Any]) -> str:
        return "Here is a clean summary of your portfolio's recent performance."


def _make_uap(subject: str, validation_status: ValidationStatus) -> UAP:
    return UAP(
        subject=subject,
        information_class=InformationClass.ESTIMATE,
        validation_status=validation_status,
        result="some result",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_disclosure_appears_even_when_generator_says_nothing_about_status():
    provisional = _make_uap("forecast A", ValidationStatus.PROVISIONAL)

    explanation = explain_with_disclosure([provisional], SilentOnStatusGenerator())

    assert "validation_status=PROVISIONAL" in "".join(explanation.limitations)
    assert "PROVISIONAL" in explanation.result


def test_verified_items_get_no_disclosure_note():
    verified = _make_uap("fact A", ValidationStatus.VERIFIED)
    explanation = explain_with_disclosure([verified], StubExplanationGenerator())
    assert explanation.limitations == []


def test_no_disclosures_needed_result_is_real_narrative_not_none():
    """
    Code Quality Verification finding #7: when there's nothing to
    disclose, `full_text = narrative` (never overwritten) must produce
    the real generator output, not None.
    """
    verified = _make_uap("fact A", ValidationStatus.VERIFIED)
    explanation = explain_with_disclosure([verified], StubExplanationGenerator())
    assert explanation.limitations == []
    assert explanation.result is not None
    assert isinstance(explanation.result, str)
    assert "STUB" in explanation.result  # confirms it's the real generator output


def test_mixed_inputs_only_disclose_non_verified_ones():
    verified = _make_uap("fact A", ValidationStatus.VERIFIED)
    conflicted = _make_uap("estimate B", ValidationStatus.CONFLICTED)
    stale = _make_uap("estimate C", ValidationStatus.STALE)

    explanation = explain_with_disclosure(
        [verified, conflicted, stale], StubExplanationGenerator()
    )

    assert len(explanation.limitations) == 2
    joined = "".join(explanation.limitations)
    assert "fact A" not in joined
    assert "estimate B" in joined and "CONFLICTED" in joined
    assert "estimate C" in joined and "STALE" in joined


def test_all_input_ids_appear_in_dependencies():
    verified = _make_uap("fact A", ValidationStatus.VERIFIED)
    provisional = _make_uap("estimate B", ValidationStatus.PROVISIONAL)

    explanation = explain_with_disclosure([verified, provisional], StubExplanationGenerator())

    assert verified.id in explanation.dependencies
    assert provisional.id in explanation.dependencies


# --- Recursive disclosure via known_uaps (the Attack 3 fix), and the
# --- never-silently-incomplete fix layered on top of it ---


def _make_uap_with_deps(
    subject: str, validation_status: ValidationStatus, dependencies: list[str]
) -> UAP:
    return UAP(
        subject=subject,
        information_class=InformationClass.ESTIMATE,
        validation_status=validation_status,
        result="some result",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=dependencies,
    )


def test_unresolved_dependency_produces_an_incompleteness_note_not_silence():
    """
    The gap this task closes: previously, omitting known_uaps meant a
    top-level UAP's own unresolved dependencies were silently ignored —
    a VERIFIED-looking judgement with a genuinely unresolvable
    PROVISIONAL ancestor produced an empty, clean-looking disclosure.
    Now it must say it couldn't check.
    """
    buried = _make_uap("buried fact", ValidationStatus.PROVISIONAL)
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, [buried.id])

    explanation = explain_with_disclosure([top], StubExplanationGenerator())

    assert explanation.limitations != []
    joined = " ".join(explanation.limitations)
    assert "top judgement" in joined
    assert "could not be resolved" in joined
    assert buried.id in joined


def test_true_leaf_uap_produces_no_spurious_incompleteness_note():
    """
    A UAP with no dependencies/provenance_chain at all has nothing
    unresolved — confirms the fix doesn't over-trigger.
    """
    leaf = _make_uap("standalone fact", ValidationStatus.VERIFIED)
    explanation = explain_with_disclosure([leaf], StubExplanationGenerator())
    assert explanation.limitations == []


def test_uaps_referencing_each_other_directly_need_no_known_uaps():
    """
    A reference that points at another UAP already in the top-level
    `uaps` list is resolved from that list itself — a caller who passes
    a complete, self-contained set doesn't need known_uaps just to
    cross-reference within it.
    """
    buried = _make_uap("buried fact", ValidationStatus.PROVISIONAL)
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, [buried.id])

    explanation = explain_with_disclosure([buried, top], StubExplanationGenerator())

    joined = " ".join(explanation.limitations)
    assert "buried fact" in joined and "PROVISIONAL" in joined
    assert "could not be resolved" not in joined


def test_known_uaps_walks_multiple_hops_and_discloses_buried_provisional():
    buried_fact = _make_uap("buried fact", ValidationStatus.PROVISIONAL)
    middle = _make_uap_with_deps("middle estimate", ValidationStatus.VERIFIED, [buried_fact.id])
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, [middle.id])

    known_uaps = {u.id: u for u in [buried_fact, middle, top]}
    explanation = explain_with_disclosure([top], StubExplanationGenerator(), known_uaps=known_uaps)

    joined = " ".join(explanation.limitations)
    assert "buried fact" in joined
    assert "PROVISIONAL" in joined


def test_unresolved_reference_is_flagged_not_silently_skipped():
    top = _make_uap_with_deps("top judgement", ValidationStatus.VERIFIED, ["nonexistent-id"])

    explanation = explain_with_disclosure([top], StubExplanationGenerator(), known_uaps={})

    joined = " ".join(explanation.limitations)
    assert "nonexistent-id" in joined
    assert "could not be resolved" in joined


def test_diamond_shaped_graph_continues_past_shared_ancestor_to_discover_unique_branches():
    """
    Code Quality Verification finding #6. On re-inspection while
    implementing this fix, the traversal's continue-vs-break logic was
    already correct here (mutation testing showed what WOULD break if
    continue were mutated to break, not that it currently is broken) —
    this was a test-coverage gap on already-correct code, not a live
    behavior bug, so no code change was made; see the accompanying
    report for the explicit flag on this point.

    A diamond-shaped graph: two branches (left, right) share one common
    ancestor. The shared ancestor is discovered via one branch first;
    when the OTHER branch later references that same (already-resolved)
    ancestor, the loop must continue processing THAT branch's own
    remaining, unique reference — not abort the whole walk. If it
    aborted (the continue-vs-break regression this guards against), the
    branch's own unique descendant would never be discovered, silently
    under-disclosing it — exactly the class of bug this project has
    already spent multiple tasks fixing elsewhere in this same function.

    Precisely: this exercises the `if ref_id in reached: continue` skip
    (a reference resolving to a node already reached via another path).
    _walk_all_dependencies has a SECOND, distinct continue-vs-break site
    — `if current.id in expanded: continue`, guarding against the same
    node being popped off the to_expand worklist twice — which this
    diamond graph does NOT exercise: because `reached` is marked
    synchronously at the moment a node is first discovered (before it's
    ever pushed a second time), no node discovered purely by following
    dependencies/provenance_chain can ever be pushed onto to_expand
    twice. That second site is only reachable when the *caller* passes
    a duplicate id directly in `start_uaps` — see
    test_duplicate_start_uap_id_does_not_abort_the_rest_of_the_walk
    below for that distinct case.
    """
    shared_ancestor = _make_uap("shared ancestor fact", ValidationStatus.PROVISIONAL)
    left_unique = _make_uap("left-only fact", ValidationStatus.PROVISIONAL)
    right_unique = _make_uap("right-only fact", ValidationStatus.PROVISIONAL)
    left_branch = _make_uap_with_deps(
        "left branch", ValidationStatus.VERIFIED, [shared_ancestor.id, left_unique.id]
    )
    right_branch = _make_uap_with_deps(
        "right branch", ValidationStatus.VERIFIED, [shared_ancestor.id, right_unique.id]
    )
    top = _make_uap_with_deps(
        "top judgement", ValidationStatus.VERIFIED, [left_branch.id, right_branch.id]
    )

    known_uaps = {
        u.id: u
        for u in [shared_ancestor, left_unique, right_unique, left_branch, right_branch, top]
    }
    explanation = explain_with_disclosure([top], StubExplanationGenerator(), known_uaps=known_uaps)

    joined = " ".join(explanation.limitations)
    # All three genuinely-PROVISIONAL nodes must be disclosed — including
    # BOTH branch-unique leaves, proving neither branch was cut short
    # when it hit the already-resolved shared ancestor.
    assert "shared ancestor fact" in joined
    assert "left-only fact" in joined
    assert "right-only fact" in joined


def test_duplicate_start_uap_id_does_not_abort_the_rest_of_the_walk():
    """
    Precise companion to the diamond-graph test above, targeting
    _walk_all_dependencies' OTHER continue-vs-break site: `if
    current.id in expanded: continue`. As explained in the diamond
    test's docstring, this branch is unreachable via ordinary
    dependency-following (a node is marked `reached` the instant it's
    first discovered, before it could ever be pushed onto the
    to_expand worklist a second time) — the only way to make
    `current.id in expanded` true is for the CALLER's own `start_uaps`
    list to contain the same id twice, so that id is pushed onto
    to_expand twice up front.

    to_expand is a stack (list.pop() takes the last element), so
    start_uaps is arranged as [c_node, a_node, a_node]: both copies of
    a_node are popped and processed FIRST (a_node's own resolvable
    dependency d_node included), and only THEN is c_node — still
    sitting underneath them on the stack — popped. When the second
    a_node copy is popped, it must be skipped (continue) so the walk
    keeps going and still reaches c_node afterwards; a wrongful abort
    (break) would leave c_node on the worklist forever, so its own
    unresolved dependency ("missing-c-dep") would never even be
    checked, let alone disclosed — despite c_node itself still showing
    up in the result (it's pre-seeded into `reached` from start_uaps
    directly, independent of ever being expanded), so only the
    unresolved-dependency note distinguishes correct from mutant here.
    """
    d_node = _make_uap("d-node (a_node's resolvable dependency)", ValidationStatus.VERIFIED)
    a_node = _make_uap_with_deps("a-node", ValidationStatus.VERIFIED, [d_node.id])
    c_node = _make_uap_with_deps("c-node", ValidationStatus.VERIFIED, ["missing-c-dep"])

    known_uaps = {u.id: u for u in [d_node, a_node, c_node]}
    explanation = explain_with_disclosure(
        [c_node, a_node, a_node], StubExplanationGenerator(), known_uaps=known_uaps
    )

    joined = " ".join(explanation.limitations)
    assert "missing-c-dep" in joined


def test_multiple_unresolved_dependencies_on_one_node_are_all_reported():
    """
    Targets _walk_all_dependencies' third continue-vs-break site: after
    recording one unresolved reference, the loop must `continue` on to
    check this node's REMAINING references — not `break` out of the
    whole for-loop, which would silently stop after the first missing
    reference and never even look at the rest (whether they're
    themselves unresolved, or perfectly resolvable).
    """
    resolvable = _make_uap("resolvable dependency", ValidationStatus.VERIFIED)
    top = _make_uap_with_deps(
        "top judgement",
        ValidationStatus.VERIFIED,
        ["missing-id-one", "missing-id-two", resolvable.id],
    )

    known_uaps = {u.id: u for u in [resolvable, top]}
    explanation = explain_with_disclosure([top], StubExplanationGenerator(), known_uaps=known_uaps)

    joined = " ".join(explanation.limitations)
    assert "missing-id-one" in joined
    assert "missing-id-two" in joined
    # The resolvable dependency after the two missing ones must still
    # have been reached and checked, not skipped by an early abort.
    assert "resolvable dependency" not in joined  # it's VERIFIED, so no disclosure note


def test_partial_known_uaps_names_specifically_which_reference_is_unresolved():
    """
    known_uaps resolves one of two dependencies but not the other — the
    note must name only the genuinely unresolved one, not a generic
    catch-all covering both.
    """
    resolvable = _make_uap("resolvable ancestor", ValidationStatus.VERIFIED)
    top = _make_uap_with_deps(
        "top judgement", ValidationStatus.VERIFIED, [resolvable.id, "still-missing-id"]
    )

    explanation = explain_with_disclosure(
        [top], StubExplanationGenerator(), known_uaps={resolvable.id: resolvable}
    )

    joined = " ".join(explanation.limitations)
    assert "still-missing-id" in joined
    assert resolvable.id not in joined  # the resolved one is not named as unresolved
    assert "could not be resolved" in joined
