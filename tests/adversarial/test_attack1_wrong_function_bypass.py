"""
Attack 1 — The Wrong-Function Bypass.

Scenario: a caller uses minimize_variance (the uncapped Section 5.1
solver) where minimize_variance_with_loss_cap should have been used —
either by mistake, or because nothing in the codebase forces the
loss-capped variant to be chosen. This attack checks two separate
things:

1. When verify_loss_cap_candidate IS actually called on the resulting
   candidate, does it correctly catch the breach? (It does — this part
   is expected to hold, and is tested here for completeness rather than
   as the main finding.)
2. Is there anything in the current codebase that FORCES verification to
   happen at all, or structurally blocks a REJECTED candidate from being
   used downstream — or is the entire verification step something a
   caller can simply skip?

UPDATE (post-fix): frame_candidate now enforces VERIFICATION_FRAMEWORK.md
Section 8 directly — a REJECTED candidate raises by default, and
proceeding requires an explicit, logged override_reason (see
test_part2c below, re-run against the exact same scenario that
originally found this gap). Parts 2a/2b's findings — that verification
itself is still not structurally mandatory before framing, and that the
disclosure mechanism's *generic* PROVISIONAL note still doesn't name the
specific breach — remain true and are unchanged by this fix; only the
REJECTED-specific laundering in Part 2c has been closed.
"""

import pytest
from optifi_ai import StubExplanationGenerator, explain_with_disclosure, frame_candidate
from optifi_optimisation import minimize_variance
from optifi_quant import parametric_var
from optifi_shared import ValidationStatus
from optifi_verification import VerdictType, apply_verdict, verify_loss_cap_candidate

# A deliberately high-risk two-asset combination: with only two assets,
# sum(w)=1 and w.mu=target_return pin down a single feasible point, so
# minimize_variance has no freedom to avoid the risk — it must return
# this exact, high-variance allocation.
EXPECTED_RETURNS = {"A": 0.05, "B": 0.20}
COVARIANCE = {"A": {"A": 0.01, "B": 0.0}, "B": {"A": 0.0, "B": 0.25}}
TARGET_RETURN = 0.15
PORTFOLIO_VALUE = 100_000.0
CONFIDENCE_LEVEL = 0.95
MAX_SINGLE_PERIOD_LOSS = 5_000.0  # a realistic, tight mandate cap


def _build_bypass_candidate():
    """The uncapped solver, called where the capped one should have been."""
    return minimize_variance(
        EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN, min_weight=0.0, max_weight=1.0
    )


def test_part1_verify_loss_cap_candidate_catches_the_breach_when_actually_called():
    """
    Confirms the checking mechanism itself works, in isolation — this is
    NOT the adversarial finding, just establishing that the guardrail is
    at least capable of catching this, before Part 2 asks whether
    anything makes it actually run.
    """
    candidate = _build_bypass_candidate()
    weights = candidate.result["weights"]

    # Sanity: this candidate really is dangerous — VaR is ~11x the cap.
    std_dev = candidate.result["portfolio_variance"] ** 0.5
    real_var = parametric_var(
        portfolio_value=PORTFOLIO_VALUE, portfolio_std_dev=std_dev, confidence_level=CONFIDENCE_LEVEL
    ).result
    assert real_var > MAX_SINGLE_PERIOD_LOSS * 5

    verdict = verify_loss_cap_candidate(
        weights,
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=MAX_SINGLE_PERIOD_LOSS,
        confidence_level=CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    assert verdict.verdict_type == VerdictType.REJECT


def test_part2a_nothing_forces_the_candidate_through_verification_before_framing():
    """
    THE ADVERSARIAL FINDING: frame_candidate accepts the raw,
    never-verified, loss-cap-breaching candidate with zero error, zero
    warning, and no inspection of whether any verification step ever
    ran. There is no code path that requires verify_loss_cap_candidate
    (or anything else) to be called before a candidate reaches ai-engine.
    Verification exists only as a function a caller may or may not
    invoke, not as a gate.
    """
    candidate = _build_bypass_candidate()

    # No exception, no warning, nothing — frame_candidate has no
    # mechanism to know or care that this candidate breaches any cap.
    framed = frame_candidate(candidate, StubExplanationGenerator())

    assert framed.result["original_figures"] == candidate.result
    # The candidate's own validation_status is untouched by any
    # verification step, because none ran.
    assert candidate.validation_status == ValidationStatus.PROVISIONAL


def test_part2b_disclosure_only_shows_generic_provisional_not_the_specific_breach():
    """
    Even the one guardrail that DOES fire automatically — explain_with_
    disclosure's non-VERIFIED flag — only reports the generic
    "PROVISIONAL, not VERIFIED" note. It has no awareness that a loss
    cap exists, was breached, or was never checked. A user reading this
    disclosure sees a routine trust-level caveat, not "this candidate
    violates your stated risk limit by 11x."
    """
    candidate = _build_bypass_candidate()
    framed = frame_candidate(candidate, StubExplanationGenerator())

    explanation = explain_with_disclosure([framed], StubExplanationGenerator())

    disclosure_text = " ".join(explanation.limitations)
    assert "PROVISIONAL" in disclosure_text  # the generic flag does fire
    assert "loss cap" not in disclosure_text.lower()  # but says nothing specific
    assert "5,000" not in disclosure_text and "5000" not in disclosure_text


def test_part2c_re_test_rejected_candidate_now_blocked_by_default():
    """
    RE-TEST (post-fix), using the exact same scenario that originally
    found this gap: a REJECTED candidate now correctly raises when
    passed to frame_candidate without an override. Before the fix, this
    silently succeeded and even overwrote the REJECTED status to a plain
    PROVISIONAL in the framed output — see
    test_part2c_re_test_genuine_override_succeeds_and_is_logged below
    for confirmation the override path works and is visible.
    """
    candidate = _build_bypass_candidate()
    weights = candidate.result["weights"]
    verdict = verify_loss_cap_candidate(
        weights,
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=MAX_SINGLE_PERIOD_LOSS,
        confidence_level=CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    assert verdict.verdict_type == VerdictType.REJECT

    rejected_candidate = apply_verdict(candidate, verdict)
    assert rejected_candidate.validation_status == ValidationStatus.REJECTED

    # The exploit no longer works: this now raises instead of silently
    # proceeding.
    with pytest.raises(ValueError, match="REJECTED"):
        frame_candidate(rejected_candidate, StubExplanationGenerator())


def test_part2c_re_test_genuine_override_succeeds_and_is_logged():
    """
    The legitimate escape hatch VERIFICATION_FRAMEWORK.md Section 8
    describes — "must not be used downstream without an explicit,
    logged override" — now actually exists and is exercised here against
    the same REJECTED candidate from Part 2c.
    """
    candidate = _build_bypass_candidate()
    weights = candidate.result["weights"]
    verdict = verify_loss_cap_candidate(
        weights,
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=MAX_SINGLE_PERIOD_LOSS,
        confidence_level=CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    rejected_candidate = apply_verdict(candidate, verdict)

    framed = frame_candidate(
        rejected_candidate,
        StubExplanationGenerator(),
        override_rejection=True,
        override_reason="manual risk-committee sign-off, ticket OPTIFI-9001",
    )

    assert framed.result["original_figures"] == rejected_candidate.result
    # The "logged" half of "explicit, logged override" — visible in the
    # framed output itself, not silently dropped.
    joined_limitations = " ".join(framed.limitations)
    assert "REJECTED" in joined_limitations
    assert "OPTIFI-9001" in joined_limitations
