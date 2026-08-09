"""
Attack 2 — Corroboration String-Matching Robustness.

ANALYTICAL_CONTRACT_SPEC.md Section 4a requires independent corroboration
that "does not share a common upstream origin" — its own worked example
is "two outlets both republishing the same wire report... does not
count." This attack originally found that corroborate_fact's independence
check was exact string equality on `source`, so "BBC News" (etc.) was
wrongly accepted as independent from "BBC."

UPDATE (post-fix): corroborate_fact's independence check now normalizes
case/whitespace and checks substring relationships in either direction
(data-engine/optifi_data/corroboration.py's `_same_origin`). This is a
bounded improvement, not full entity resolution — see
test_full_corporate_name_remains_a_known_limitation below for the
specific pair that is still not caught, and
data-engine/tests/test_corroboration.py for the complete, empirically-
verified results for all four original variants (one of which —
"bbc.co.uk" — turned out to be caught too, a stronger result than
assumed when this fix was scoped; reported honestly there rather than
silently matching the original prediction).
"""

from optifi_data import corroborate_fact
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus


def _make_fact(source: str) -> UAP:
    return UAP(
        subject="Bank of England signalled a rate cut",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result="Bank of England signalled a rate cut",
        source=source,
        producer="data-engine (test)",
        confidence=ConfidenceLevel.LOW,
    )


def test_re_test_differently_worded_same_outlet_now_correctly_rejected():
    """
    RE-TEST (post-fix), the exact original scenario: "BBC News" is no
    longer wrongly accepted as independent from "BBC" — the fact remains
    PROVISIONAL rather than being upgraded on the strength of a single
    reworded mention of the same outlet.
    """
    provisional_fact = _make_fact(source="BBC")
    same_outlet_reworded = _make_fact(source="BBC News")

    corroborated = corroborate_fact(provisional_fact, [same_outlet_reworded])

    assert corroborated.validation_status == ValidationStatus.PROVISIONAL
    assert corroborated.evidence == []


def test_re_test_three_variants_only_the_genuinely_unmatched_one_still_counts():
    """
    RE-TEST (post-fix), the exact original scenario: of the three
    variants, "BBC News" and "bbc.co.uk" are now correctly recognised as
    the same origin and excluded. "British Broadcasting Corporation" is
    the one genuine remaining limitation — it shares no substring with
    "bbc" after normalization, so it still counts, and the fact still
    upgrades to VERIFIED on the strength of that one variant alone (not
    three, as before this fix).
    """
    provisional_fact = _make_fact(source="BBC")
    variants = [
        _make_fact(source="BBC News"),
        _make_fact(source="bbc.co.uk"),
        _make_fact(source="British Broadcasting Corporation"),
    ]

    corroborated = corroborate_fact(provisional_fact, variants)

    assert corroborated.validation_status == ValidationStatus.VERIFIED
    independent_entries = [e for e in corroborated.evidence if e.startswith("independent source:")]
    assert len(independent_entries) == 1
    assert "British Broadcasting Corporation" in independent_entries[0]
    assert not any("BBC News" in e for e in independent_entries)
    assert not any("bbc.co.uk" in e for e in independent_entries)


def test_full_corporate_name_remains_a_known_limitation():
    """
    The honest, documented remaining gap: "British Broadcasting
    Corporation" shares no substring with "bbc" after normalization, so
    the bounded heuristic still treats it as genuinely independent from
    "BBC" — real entity resolution, not attempted here, would be needed
    to close this specific case.
    """
    provisional_fact = _make_fact(source="BBC")
    full_corporate_name = _make_fact(source="British Broadcasting Corporation")

    corroborated = corroborate_fact(provisional_fact, [full_corporate_name])

    assert corroborated.validation_status == ValidationStatus.VERIFIED


def test_control_genuinely_different_outlets_correctly_count_as_independent():
    """
    Control case: genuinely distinct outlets (not a wording variant of
    the same one) still correctly count as independent — confirming the
    fix doesn't over-trigger.
    """
    provisional_fact = _make_fact(source="BBC")
    genuinely_different = _make_fact(source="Financial Times")

    corroborated = corroborate_fact(provisional_fact, [genuinely_different])

    assert corroborated.validation_status == ValidationStatus.VERIFIED


def test_exact_duplicate_source_string_is_correctly_rejected():
    """
    Control case: a literal duplicate string was already correctly
    caught before this fix, and remains so.
    """
    provisional_fact = _make_fact(source="BBC")
    literal_republication = _make_fact(source="BBC")

    corroborated = corroborate_fact(provisional_fact, [literal_republication])

    assert corroborated.validation_status == ValidationStatus.PROVISIONAL
    assert corroborated.evidence == []
