"""
Tests for corroborate_fact (ANALYTICAL_CONTRACT_SPEC.md, Section 4a) — in
particular the shared-origin rejection rule.
"""

import pytest
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_data import corroborate_fact


def _make_uap(
    source: str,
    information_class: InformationClass = InformationClass.FACT,
    validation_status: ValidationStatus = ValidationStatus.PROVISIONAL,
) -> UAP:
    return UAP(
        subject="illustrative claim",
        information_class=information_class,
        validation_status=validation_status,
        result="illustrative claim result",
        source=source,
        producer="data-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_successful_corroboration_with_one_independent_source():
    provisional_fact = _make_uap(source="Outlet A")
    candidate = _make_uap(source="Outlet B")

    result = corroborate_fact(provisional_fact, [candidate])

    assert result.validation_status == ValidationStatus.VERIFIED
    assert any("Outlet B" in entry for entry in result.evidence)


def test_shared_origin_candidates_do_not_corroborate():
    """
    The critical test: provisional_fact and both candidates all share the
    identical `source` value — a republication scenario
    (ANALYTICAL_CONTRACT_SPEC.md Section 4a's explicit example). This
    must NOT corroborate.
    """
    provisional_fact = _make_uap(source="Wire Service X")
    candidate_1 = _make_uap(source="Wire Service X")
    candidate_2 = _make_uap(source="Wire Service X")

    result = corroborate_fact(provisional_fact, [candidate_1, candidate_2])

    assert result.validation_status == ValidationStatus.PROVISIONAL


def test_no_candidate_sources_remains_provisional():
    provisional_fact = _make_uap(source="Outlet A")

    result = corroborate_fact(provisional_fact, [])

    assert result.validation_status == ValidationStatus.PROVISIONAL


def test_structured_cross_check_with_single_verified_fact():
    provisional_fact = _make_uap(source="Outlet A")
    verified_fact = _make_uap(
        source="Official Statistics Release",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
    )

    result = corroborate_fact(provisional_fact, [verified_fact])

    assert result.validation_status == ValidationStatus.VERIFIED
    assert any("structured cross-check" in entry for entry in result.evidence)


def test_two_candidates_sharing_a_source_with_each_other_count_once_not_twice():
    """
    Two candidates whose source differs from provisional_fact's, but
    matches each other's, still succeed via that one genuinely
    independent source — but must be recorded once, not twice
    (Section 4a: "so that two republications of the same wire story or
    press release cannot corroborate each other" into double-counting).
    """
    provisional_fact = _make_uap(source="Outlet A")
    candidate_1 = _make_uap(source="Outlet B")
    candidate_2 = _make_uap(source="Outlet B")

    result = corroborate_fact(provisional_fact, [candidate_1, candidate_2])

    assert result.validation_status == ValidationStatus.VERIFIED
    outlet_b_entries = [entry for entry in result.evidence if "Outlet B" in entry]
    assert len(outlet_b_entries) == 1


# --- Fix 1: bounded same-origin matching (tests/adversarial's Attack 2) ---
#
# Real, empirically-verified results for all four original adversarial
# source variants against "BBC" — not assumed, checked directly:
#   "BBC" vs "BBC News"                        -> caught (substring match)
#   "BBC" vs " bbc "                           -> caught (normalization)
#   "BBC" vs "bbc.co.uk"                       -> caught (substring match:
#       "bbc" is literally a contiguous substring of "bbc.co.uk", so this
#       pair IS caught by the bounded heuristic — a stronger result than
#       originally assumed when this fix was scoped, called out here
#       rather than left as a silent surprise)
#   "BBC" vs "British Broadcasting Corporation" -> still NOT caught (no
#       shared substring after normalization) — the genuine, documented
#       remaining limitation. Real entity resolution would be needed to
#       close this one.


def test_bbc_vs_bbc_news_now_correctly_fails_to_corroborate():
    provisional_fact = _make_uap(source="BBC")
    same_outlet_reworded = _make_uap(source="BBC News")

    result = corroborate_fact(provisional_fact, [same_outlet_reworded])

    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.evidence == []


def test_bbc_vs_whitespace_padded_lowercase_bbc_now_correctly_fails_to_corroborate():
    provisional_fact = _make_uap(source="BBC")
    normalized_variant = _make_uap(source=" bbc ")

    result = corroborate_fact(provisional_fact, [normalized_variant])

    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.evidence == []


def test_bbc_vs_bbc_co_uk_is_also_caught_a_stronger_result_than_originally_assumed():
    """
    Not part of the original two required cases, but worth confirming
    explicitly and honestly: "bbc" is a literal contiguous substring of
    "bbc.co.uk", so the bounded substring heuristic catches this pair
    too — contrary to the assumption under which this fix was scoped
    ("bbc.co.uk" expected to remain a known limitation). Reporting this
    plainly rather than silently matching the original prediction.
    """
    provisional_fact = _make_uap(source="BBC")
    domain_variant = _make_uap(source="bbc.co.uk")

    result = corroborate_fact(provisional_fact, [domain_variant])

    assert result.validation_status == ValidationStatus.PROVISIONAL
    assert result.evidence == []


def test_bbc_vs_full_corporate_name_remains_a_known_limitation():
    """
    The genuine, still-open limitation: "British Broadcasting
    Corporation" shares no substring with "bbc" after normalization, so
    the bounded heuristic cannot recognise these as the same outlet.
    Real entity resolution — not attempted here — would be needed to
    close this specific gap.
    """
    provisional_fact = _make_uap(source="BBC")
    full_corporate_name = _make_uap(source="British Broadcasting Corporation")

    result = corroborate_fact(provisional_fact, [full_corporate_name])

    # Documents the actual (limited) behavior — this candidate is
    # incorrectly treated as independent, exactly like before this fix.
    assert result.validation_status == ValidationStatus.VERIFIED


def test_same_origin_empty_string_does_not_falsely_match_everything():
    """
    Code Quality Verification finding #4. Direct unit test on the
    private helper: without the `if not normalized_a or not
    normalized_b:` guard, an empty-string source would be treated as "a
    substring of" (hence same-origin as) every other source, since
    Python's `"" in anything` is True. On re-inspection while
    implementing this fix, the guard's existing `or` (not `and`) is
    already correct — this was a genuine test-coverage gap, not a live
    behavior bug, so no code change was made here; see the accompanying
    report for the explicit flag on this point.
    """
    from optifi_data.corroboration import _same_origin

    assert _same_origin("", "Reuters") is False
    assert _same_origin("Reuters", "") is False
    assert _same_origin("", "Financial Times") is False


def test_same_origin_substring_match_is_direction_independent():
    """
    Follow-up finding, surfaced (not requested) by the mutation-testing
    re-run in the prior fix task: mutmut_10 changes the final line's
    FIRST `or` to `and` —

        normalized_a == normalized_b or normalized_a in normalized_b or normalized_b in normalized_a
        normalized_a == normalized_b and normalized_a in normalized_b or normalized_b in normalized_a

    Python's `and`/`or` precedence makes the mutant equivalent to
    `(a == b and a in b) or (b in a)` — which silently drops the
    `a in b` disjunct whenever a != b, leaving only the `b in a`
    direction live. Concretely: source_a="BBC", source_b="BBC News".
    a==b is False. a in b ("bbc" in "bbc news") is True, so the
    ORIGINAL correctly returns True (same origin) — but the mutant's
    `(False and True) or ("bbc news" in "bbc")` evaluates to
    `False or False` = False, wrongly treating them as different
    origins. This direction matters in practice: corroborate_fact
    calls `_same_origin(candidate.source, seen)` — candidate.source is
    always the FIRST argument — so a shorter candidate source (e.g.
    "BBC") naming the same outlet as a longer already-seen source
    (e.g. "BBC News") is exactly the shape this mutant breaks. The
    REVERSE direction — source_a longer and containing source_b, as in
    test_bbc_vs_bbc_co_uk_is_also_caught_a_stronger_result_than_
    originally_assumed above, where candidate.source="bbc.co.uk" is
    checked against provisional_fact.source="BBC" — only exercises the
    `b in a` disjunct, which the mutant leaves untouched; that's
    exactly why that existing test alone doesn't kill this mutant.
    """
    from optifi_data.corroboration import _same_origin

    assert _same_origin("BBC", "BBC News") is True
    assert _same_origin("Reuters", "Reuters UK") is True
    # Sanity: the reverse direction (already covered elsewhere) still
    # holds too — this isn't testing a one-way fix, just closing the
    # gap in the direction the mutant actually breaks.
    assert _same_origin("BBC News", "BBC") is True


def test_corroborate_fact_with_empty_source_provisional_fact_still_corroborates_normally():
    """Integration-level companion: a real (non-empty) candidate source
    still corroborates correctly even when provisional_fact.source is
    empty — proving the empty-source guard doesn't accidentally block
    genuine corroboration either."""
    provisional_fact = _make_uap(source="")
    candidate = _make_uap(source="Reuters")

    result = corroborate_fact(provisional_fact, [candidate])

    assert result.validation_status == ValidationStatus.VERIFIED


def test_genuinely_independent_outlets_still_correctly_corroborate():
    """Confirms the fix doesn't over-trigger on real, unrelated outlets."""
    provisional_fact = _make_uap(source="Reuters")
    genuinely_different = _make_uap(source="Financial Times")

    result = corroborate_fact(provisional_fact, [genuinely_different])

    assert result.validation_status == ValidationStatus.VERIFIED
    assert any("Financial Times" in entry for entry in result.evidence)


def test_does_not_mutate_provisional_fact_or_candidates():
    provisional_fact = _make_uap(source="Outlet A")
    candidate = _make_uap(source="Outlet B")

    provisional_fact_before = provisional_fact.model_dump()
    candidate_before = candidate.model_dump()

    corroborate_fact(provisional_fact, [candidate])

    assert provisional_fact.model_dump() == provisional_fact_before
    assert candidate.model_dump() == candidate_before


def test_corroborated_result_unaffected_by_later_mutation_of_original_nested_field():
    """
    Code Quality Verification finding #5: proves the deep=True copy
    guarantee for NESTED mutable fields specifically — model_dump()
    equality snapshots (as in test_does_not_mutate_provisional_fact_
    or_candidates above) wouldn't necessarily catch a regression to a
    shallow copy, since that test only compares snapshots taken before
    corroborate_fact ever runs. This test instead mutates the ORIGINAL's
    nested list AFTER corroboration and confirms the returned UAP is
    unaffected — which would fail under deep=False, since a shallow copy
    shares the same underlying list object.
    """
    provisional_fact = _make_uap(source="Outlet A")
    provisional_fact.assumptions.append("original assumption")
    candidate = _make_uap(source="Outlet B")

    corroborated = corroborate_fact(provisional_fact, [candidate])

    # Mutate the ORIGINAL's nested list AFTER corroboration.
    provisional_fact.assumptions.append("mutated after the fact")

    assert "mutated after the fact" not in corroborated.assumptions
    assert corroborated.assumptions == ["original assumption"]


def test_no_corroboration_found_result_unaffected_by_later_mutation_of_original_nested_field():
    """
    Companion to the test above, covering corroborate_fact's OTHER
    model_copy(deep=True) call — the no-corroboration-found early return
    (used when every candidate shares the provisional_fact's own
    origin) is a separate call site with its own independent deep=True
    guarantee, not exercised by the successful-corroboration test above.
    """
    provisional_fact = _make_uap(source="Outlet A")
    provisional_fact.assumptions.append("original assumption")
    same_origin_candidate = _make_uap(source="Outlet A")

    result = corroborate_fact(provisional_fact, [same_origin_candidate])
    assert result.validation_status == ValidationStatus.PROVISIONAL

    provisional_fact.assumptions.append("mutated after the fact")

    assert "mutated after the fact" not in result.assumptions
    assert result.assumptions == ["original assumption"]


def test_raises_clear_error_when_provisional_fact_is_not_fact_provisional():
    not_provisional = _make_uap(
        source="Outlet A",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
    )
    with pytest.raises(ValueError):
        corroborate_fact(not_provisional, [_make_uap(source="Outlet B")])


def test_raises_clear_error_when_provisional_fact_is_not_information_class_fact():
    an_estimate = _make_uap(
        source="Outlet A",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
    )
    with pytest.raises(ValueError):
        corroborate_fact(an_estimate, [_make_uap(source="Outlet B")])
