"""
Attack 2 — Corroboration String-Matching Robustness.

ANALYTICAL_CONTRACT_SPEC.md Section 4a requires independent corroboration
that "does not share a common upstream origin" — its own worked example
is "two outlets both republishing the same wire report... does not
count." This attack asks: does corroborate_fact's actual independence
check understand that "BBC," "BBC News," and "bbc.co.uk" plausibly name
the same real-world outlet, or does it only compare source strings for
exact equality?
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


def test_differently_worded_same_outlet_is_wrongly_treated_as_independent():
    """
    THE ADVERSARIAL FINDING: corroborate_fact's independence check is
    exact string equality on `source` (`candidate.source not in
    seen_sources`). "BBC News" is not the string "BBC", so it is
    accepted as a genuinely independent corroborating source — even
    though a human would immediately recognise both plausibly name the
    same real-world outlet, which Section 4a's own wire-report example
    says must NOT count.
    """
    provisional_fact = _make_fact(source="BBC")
    same_outlet_reworded = _make_fact(source="BBC News")

    corroborated = corroborate_fact(provisional_fact, [same_outlet_reworded])

    # The gap: this upgrades to VERIFIED on the strength of a single
    # source that is very plausibly the same outlet as the original,
    # just worded differently.
    assert corroborated.validation_status == ValidationStatus.VERIFIED


def test_three_variants_of_the_same_outlet_all_count_as_separately_independent():
    """
    Worse: because the check is purely pairwise string inequality, EVERY
    differently-worded variant of the same outlet counts as yet another
    independent source, stacking up "independent" corroboration entries
    that are actually all the same outlet.
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
    assert len(independent_entries) == 3  # all three "count" despite being one real outlet


def test_control_genuinely_different_outlets_correctly_count_as_independent():
    """
    Control case, to isolate the actual gap: genuinely distinct outlets
    (not a wording variant of the same one) SHOULD count as independent
    — confirming the mechanism isn't broken outright, only that it can't
    distinguish "differently worded, same outlet" from "actually
    different outlet."
    """
    provisional_fact = _make_fact(source="BBC")
    genuinely_different = _make_fact(source="Financial Times")

    corroborated = corroborate_fact(provisional_fact, [genuinely_different])

    assert corroborated.validation_status == ValidationStatus.VERIFIED


def test_exact_duplicate_source_string_is_correctly_rejected():
    """
    Control case: the ONE thing the exact-string check does correctly
    catch is a literal duplicate string — confirming the check isn't
    completely absent, just too narrow to catch superficial rewording.
    """
    provisional_fact = _make_fact(source="BBC")
    literal_republication = _make_fact(source="BBC")

    corroborated = corroborate_fact(provisional_fact, [literal_republication])

    assert corroborated.validation_status == ValidationStatus.PROVISIONAL
    assert corroborated.evidence == []
