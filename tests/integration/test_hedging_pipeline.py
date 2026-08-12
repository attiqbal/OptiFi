"""
End-to-end pipeline test for the hedging capability, alongside the
existing vertical slice: a defined-risk options structure candidate
(HEDGING_SPEC.md Section 5) through independent verification
(verification-engine, Section 7), Stage 10 candidate framing
(AI_ENGINE_SPEC.md Section 3.2), and Stage 13 user-facing explanation
with disclosure (AI_ENGINE_SPEC.md Section 3.4).

The collar/partial-coverage case is the one that matters here: it is
this project's first PASS WITH CAUTION verdict actually threaded through
the full Stage 10 -> 13 pipeline in a real test, and doing so surfaced a
genuine, general (not hedging-specific) gap in explain_with_disclosure --
see optifi_ai/disclosure.py's module docstring and the
_VERIFICATION_CAUTION_PREFIX mechanism added to fix it. These tests both
exercise that fix and stand as its own regression coverage.
"""

from __future__ import annotations

from optifi_ai import StubExplanationGenerator, explain_with_disclosure, frame_candidate
from optifi_optimisation import collar, protective_put
from optifi_verification import VerdictType, apply_verdict, verify_collar, verify_protective_put

POSITION_QUANTITY = 100
CURRENT_PRICE = 50.0
PUT_STRIKE = 45.0
PUT_PREMIUM = 2.0
CALL_STRIKE = 55.0
CALL_PREMIUM = 1.5


def _run_through_pipeline(candidate, verdict):
    """
    verify -> apply_verdict -> frame_candidate -> explain_with_disclosure,
    mirroring the vertical slice's own step7 (verification) -> step8
    (ai-engine) ordering. known_uaps carries the CAUTION-BEARING candidate
    (post apply_verdict), keyed by its id -- frame_candidate's own
    dependencies=[candidate.id, ...] is what lets explain_with_disclosure's
    dependency walk resolve back to it and pick up any caution recorded in
    its limitations.
    """
    candidate_with_verdict = apply_verdict(candidate, verdict)
    framed = frame_candidate(candidate_with_verdict, StubExplanationGenerator())
    known_uaps = {candidate_with_verdict.id: candidate_with_verdict}
    explanation = explain_with_disclosure(
        [framed], StubExplanationGenerator(), known_uaps=known_uaps
    )
    return candidate_with_verdict, framed, explanation


# --- Collar, genuine partial coverage: the PASS_WITH_CAUTION case ---


def test_collar_partial_coverage_figures_preserved_through_framing():
    """
    frame_candidate must preserve the collar's own reported figures
    (floor_price, ceiling_price, and the uncovered-quantity figures)
    exactly, unaltered -- the same guarantee already proven for other
    candidate types, now proven specifically for a hedging UAP whose
    `result` shape (floor_price/ceiling_price/collared_quantity/
    uncollared_quantity/...) frame_candidate has never been exercised
    against before this test.
    """
    candidate = collar(
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=60,  # genuine partial coverage
    )
    verdict = verify_collar(
        candidate,
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=60,
    )
    assert verdict.verdict_type == VerdictType.PASS_WITH_CAUTION

    _, framed, _ = _run_through_pipeline(candidate, verdict)

    # Exact, untouched copy -- apply_verdict only ever changes
    # limitations/validation_status, never .result, so this must match
    # the ORIGINAL (pre-verdict) candidate's own result precisely.
    assert framed.result["original_figures"] == candidate.result
    assert framed.result["original_figures"]["floor_price"] == PUT_STRIKE
    assert framed.result["original_figures"]["ceiling_price"] == CALL_STRIKE
    assert framed.result["original_figures"]["collared_quantity"] == 60
    assert framed.result["original_figures"]["uncollared_quantity"] == 40


def test_collar_partial_coverage_caution_reaches_final_disclosure():
    """
    THE key test in this module: the specific PASS WITH CAUTION reason —
    naming the 40-unit uncovered exposure — must actually appear in the
    final user-facing disclosed text, not just in verification-engine's
    own Verdict object. Proven against the real pipeline (real
    apply_verdict, real frame_candidate, real explain_with_disclosure),
    not asserted against a synthetic/mocked disclosure mechanism.
    """
    candidate = collar(
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=60,
    )
    verdict = verify_collar(
        candidate,
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=60,
    )

    _, _, explanation = _run_through_pipeline(candidate, verdict)

    assert "40" in explanation.result
    assert "PARTIAL collar" in explanation.result
    assert "uncapped, unhedged exposure" in explanation.result
    # The caution note is recorded in the final explanation's own
    # limitations too (VERIFICATION_FRAMEWORK.md Section 4: visible in
    # the "Why?" drill-down), not just folded into narrative text.
    assert any("40" in limitation for limitation in explanation.limitations)


def test_collar_partial_coverage_ordinary_limitations_are_not_leaked_as_disclosures():
    """
    Precision check on the fix: collar()'s own ORDINARY methodology
    limitations (e.g. "the payoff bounds... apply only to
    collared_quantity") must NOT appear as disclosure lines — only
    limitations carrying the specific "verification caution: " marker
    apply_verdict records. Confirms the fix is precisely scoped, not a
    blanket dump of every UAP's limitations into user-facing text.
    """
    candidate = collar(
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=60,
    )
    verdict = verify_collar(
        candidate,
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=60,
    )
    assert any(
        lim.startswith("the payoff bounds") for lim in candidate.limitations
    )  # sanity: this ordinary limitation genuinely exists on the candidate

    _, _, explanation = _run_through_pipeline(candidate, verdict)

    assert "the payoff bounds" not in explanation.result
    assert "static payoff-at-expiry" not in explanation.result


# --- Collar, fully covered: clean PASS comparison case ---


def test_collar_fully_covered_produces_no_caution_in_disclosure():
    """Contrast case: a fully-covered collar is a clean PASS -- no
    caution note should appear anywhere in the final disclosure."""
    candidate = collar(
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=100,  # fully covered
    )
    verdict = verify_collar(
        candidate,
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
        call_strike=CALL_STRIKE,
        call_premium=CALL_PREMIUM,
        call_covered_quantity=100,
    )
    assert verdict.verdict_type == VerdictType.PASS

    _, _, explanation = _run_through_pipeline(candidate, verdict)

    assert "verification caution" not in explanation.result
    assert "PARTIAL collar" not in explanation.result


# --- Protective put: simpler clean-PASS comparison case ---


def test_protective_put_clean_pass_through_full_pipeline():
    """
    Simpler comparison case: a protective put (no naked-call machinery
    involved) through the same verify -> frame -> disclose pipeline.
    Figures preserved, no caution note (a clean PASS from
    verify_protective_put), and the non-VERIFIED status is still
    correctly disclosed (Never-list item 9).
    """
    candidate = protective_put(
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
    )
    verdict = verify_protective_put(
        candidate,
        position_quantity=POSITION_QUANTITY,
        current_price=CURRENT_PRICE,
        put_strike=PUT_STRIKE,
        put_premium=PUT_PREMIUM,
    )
    assert verdict.verdict_type == VerdictType.PASS

    candidate_with_verdict, framed, explanation = _run_through_pipeline(candidate, verdict)

    # Figure preservation, proven for this UAP shape specifically.
    assert framed.result["original_figures"] == candidate.result
    assert framed.result["original_figures"]["breakeven_price"] == CURRENT_PRICE + PUT_PREMIUM
    assert framed.result["original_figures"]["upside_capped"] is False

    # No caution (clean PASS), but still correctly flagged as PROVISIONAL.
    assert "verification caution" not in explanation.result
    assert "validation_status=PROVISIONAL" in explanation.result
