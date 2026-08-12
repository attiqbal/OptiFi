"""
Tests for verify_protective_put and verify_collar (HEDGING_SPEC.md
Section 5.1/5.2/7, and Section 6's naked-call constraint).

optifi_optimisation is a [dev]/test-only dependency of this package (see
pyproject.toml) -- used here to produce genuine protective_put/collar
candidates to verify against, and to prove the naked-call rejection test
below simulates a state that never actually occurs. Production code in
hedging_checks.py does not import optifi_optimisation at all -- both
verify functions reimplement the payoff formulas directly from raw
inputs, which is what makes this genuinely independent.
"""

from optifi_optimisation import collar, protective_put
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from optifi_verification import FailureCategory, VerdictType, verify_collar, verify_protective_put


def _tampered_uap(result: dict) -> UAP:
    """A hand-built UAP standing in for a candidate whose reported
    figures don't match what the raw inputs actually produce -- never
    produced by the real protective_put/collar, simulating a bug or a
    bypassed guard."""
    return UAP(
        subject="test candidate",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="test fixture",
        producer="test fixture",
        confidence=ConfidenceLevel.MODERATE,
    )


# --- verify_protective_put ---


def test_verify_protective_put_correct_figures_passes():
    candidate = protective_put(
        position_quantity=100, current_price=50.0, put_strike=45.0, put_premium=2.0
    )
    verdict = verify_protective_put(
        candidate,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
    )
    assert verdict.verdict_type == VerdictType.PASS


def test_verify_protective_put_mismatched_max_loss_rejects_and_names_discrepancy():
    """
    A candidate hand-built with a wrong max_loss (not produced by the
    real protective_put) must be independently caught, with the specific
    reported-vs-recomputed numbers both named.
    """
    tampered = _tampered_uap({"max_loss": 999.0, "breakeven_price": 52.0})
    verdict = verify_protective_put(
        tampered,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert verdict.failure_category == FailureCategory.DATA_QUALITY
    reasons_joined = " ".join(verdict.reasons)
    assert "999.0" in reasons_joined
    assert "700.0" in reasons_joined  # the correctly recomputed max_loss


def test_verify_protective_put_mismatched_breakeven_rejects_and_names_discrepancy():
    tampered = _tampered_uap({"max_loss": 700.0, "breakeven_price": 60.0})
    verdict = verify_protective_put(
        tampered,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
    )
    assert verdict.verdict_type == VerdictType.REJECT
    reasons_joined = " ".join(verdict.reasons)
    assert "60.0" in reasons_joined
    assert "52.0" in reasons_joined  # the correctly recomputed breakeven


def test_verify_protective_put_rejects_malformed_candidate_shape():
    malformed = _tampered_uap({"narrative": "no usable payoff fields at all"})
    verdict = verify_protective_put(
        malformed,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
    )
    assert verdict.verdict_type == VerdictType.REJECT


# --- verify_collar ---


def test_verify_collar_fully_covered_correct_figures_passes_cleanly():
    candidate = collar(
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=100,
    )
    verdict = verify_collar(
        candidate,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=100,
    )
    assert verdict.verdict_type == VerdictType.PASS


def test_verify_collar_genuine_partial_coverage_produces_pass_with_caution():
    """
    THE key borderline case: a legitimate partial collar (allowed by
    collar() itself) has correct figures, but leaves real uncapped
    exposure on the uncollared portion -- PASS WITH CAUTION, naming the
    specific uncovered quantity, not a clean PASS and not a REJECT.
    """
    candidate = collar(
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=60,
    )
    verdict = verify_collar(
        candidate,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=60,
    )
    assert verdict.verdict_type == VerdictType.PASS_WITH_CAUTION
    reasons_joined = " ".join(verdict.reasons)
    assert "60" in reasons_joined
    assert "40" in reasons_joined  # the specific uncovered quantity


def test_verify_collar_mismatched_max_loss_rejects_and_names_discrepancy():
    tampered = _tampered_uap(
        {
            "floor_price": 45.0,
            "ceiling_price": 55.0,
            "net_premium_per_share": 0.5,
            "max_loss": 12345.0,  # wrong
            "max_gain": 450.0,
            "collared_quantity": 100,
            "uncollared_quantity": 0,
        }
    )
    verdict = verify_collar(
        tampered,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=100,
    )
    assert verdict.verdict_type == VerdictType.REJECT
    reasons_joined = " ".join(verdict.reasons)
    assert "12345.0" in reasons_joined
    assert "550.0" in reasons_joined  # the correctly recomputed max_loss


def test_verify_collar_bypassed_structural_guard_is_independently_caught():
    """
    THE most important test in this module (HEDGING_SPEC.md Section 6/7):
    simulates a state that should be impossible -- collar()'s own
    call_covered_quantity guard prevents this from ever being
    constructed for real, so this hand-builds a candidate as if that
    guard had somehow been bypassed, and confirms verify_collar catches
    it independently anyway, re-deriving the violation from the RAW
    call_covered_quantity/position_quantity inputs -- not by trusting
    whatever the (hypothetically compromised) candidate itself reports.
    """
    hypothetically_bypassed_candidate = _tampered_uap(
        {
            "floor_price": 45.0,
            "ceiling_price": 55.0,
            "net_premium_per_share": 0.5,
            "max_loss": 825.0,
            "max_gain": 675.0,
            "collared_quantity": 150,
            "uncollared_quantity": 0,
        }
    )
    verdict = verify_collar(
        hypothetically_bypassed_candidate,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=150,  # exceeds the held 100 units
    )
    assert verdict.verdict_type == VerdictType.REJECT
    assert verdict.failure_category == FailureCategory.DATA_QUALITY
    reasons_joined = " ".join(verdict.reasons)
    assert "150" in reasons_joined and "100" in reasons_joined
    assert "bypassed" in reasons_joined.lower()

    # And confirm, directly, that this state is unreachable via the real
    # collar() -- the structural guard this test is defending against
    # actually exists and actually fires.
    import pytest

    with pytest.raises(ValueError, match="exceeds position_quantity"):
        collar(
            position_quantity=100,
            current_price=50.0,
            put_strike=45.0,
            put_premium=2.0,
            call_strike=55.0,
            call_premium=1.5,
            call_covered_quantity=150,
        )


def test_verify_collar_rejects_malformed_candidate_shape():
    malformed = _tampered_uap({"narrative": "no usable payoff fields at all"})
    verdict = verify_collar(
        malformed,
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=100,
    )
    assert verdict.verdict_type == VerdictType.REJECT
