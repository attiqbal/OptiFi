"""
Capital Efficiency Score — QUANT_ENGINE_SPEC.md Section 7 (the six
sub-scores) and Section 8 (the composite).

Four sub-scores (Cash, Risk, Tax, Investment) have real formulas in
Section 7 and are implemented here exactly as specified — re-read fresh
from the document, not from paraphrase. Two (Debt, Liquidity) have no
formula in Section 7, only prose describing what should be penalised —
those are DESIGNED here to fill that gap. Each of those two functions'
docstrings, and the module-level constants feeding them, say so
explicitly and state the reasoning: this is an engineering decision
filling an acknowledged spec gap, not a transcription of spec content.

Every sub-score is `information_class: ESTIMATE` (Section 7's own
statement) and is explicitly bounded to [0, 100] here in code — Section
9: "Each Capital Efficiency sub-score (Section 7) must fall within its
stated 0-100 bound before the composite score is computed." This bound
is enforced explicitly via `_clamp_score` below, not merely assumed from
each formula's own shape — not every Section 7 formula's prose spells
out both a floor and a ceiling (e.g. Risk efficiency's prose states only
"floored at 0"; the 0-100 bound as a whole is Section 9's separate,
blanket requirement applying to all six).

QUANT_ENGINE_SPEC.md Section 11 item 1 is explicit that "exact weights,
bands, and thresholds ... are deliberately not fixed — calibration
against real portfolios and real outcomes is a later, empirical step."
Every numeric constant introduced here beyond the four literal Section 7
formulas (the Debt/Liquidity scaling constants, the composite's equal
weighting) is exactly that kind of placeholder — chosen to be reasonable
and clearly documented, not fitted or sourced from real data.
"""

from __future__ import annotations

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .risk_metrics import parametric_var, sharpe_ratio

# QUANT_ENGINE_SPEC.md Section 9's "must guard against a zero or
# near-zero denominator" rule, generalised here to every ratio this
# module computes (Section 9 names four specific ratios as examples;
# the same principle clearly extends to Cash/Tax/Risk/Investment
# efficiency's own denominators) — matching risk_metrics.py's own
# _STD_DEV_EPSILON in both value and intent.
_DENOMINATOR_EPSILON = 1e-9


def _clamp_score(score: float) -> float:
    """
    Section 9: every Capital Efficiency sub-score — and the composite,
    Section 8 — must fall within [0, 100]. Enforced here explicitly,
    once, rather than left to each formula's own algebra to (maybe)
    guarantee on its own.
    """
    return min(100.0, max(0.0, score))


def _require_nonzero_denominator(value: float, label: str, fn_name: str) -> None:
    if abs(value) < _DENOMINATOR_EPSILON:
        raise ValueError(
            f"{fn_name}: {label} ({value!r}) is zero or below the epsilon "
            f"threshold ({_DENOMINATOR_EPSILON}); this ratio is undefined "
            "for a (near-)zero denominator (QUANT_ENGINE_SPEC.md Section 9)."
        )


# --- Cash efficiency (QUANT_ENGINE_SPEC.md Section 7 — spec-derived) ---


def cash_efficiency(
    achieved_yield_on_cash: float,
    best_available_comparable_yield: float,
) -> UAP:
    """
    Cash efficiency (QUANT_ENGINE_SPEC.md Section 7, exact formula):

        min(100, (achieved_yield_on_cash / best_available_comparable_yield) x 100)

    `best_available_comparable_yield` has no defined data source
    anywhere in QUANT_ENGINE_SPEC.md — treated here as an assumed input
    parameter the caller supplies, the same treatment this project has
    deliberately given every other real-market-data dependency pending
    the Phase 3 vendor decision (`DATA_SOURCE_REGISTRY.md`). This
    function does not invent a data source for it.

    The spec's own formula states only the upper bound (`min(100, ...)`);
    the lower bound at 0 is added here to satisfy Section 9's separate,
    blanket 0-100 requirement for every sub-score — a negative
    achieved_yield_on_cash (e.g. a cash account whose fees exceed its
    interest) would otherwise produce a score below 0.
    """
    _require_nonzero_denominator(
        best_available_comparable_yield, "best_available_comparable_yield", "cash_efficiency"
    )

    raw_score = (achieved_yield_on_cash / best_available_comparable_yield) * 100.0
    score = _clamp_score(raw_score)

    return UAP(
        subject="Cash efficiency sub-score",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=score,
        source="computed from provided achieved_yield_on_cash, best_available_comparable_yield",
        producer="quant-engine / Cash efficiency, QUANT_ENGINE_SPEC.md Section 7",
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "achieved_yield_on_cash and best_available_comparable_yield "
            "are expressed over the same period and in consistent units",
            "best_available_comparable_yield is supplied by the caller; "
            "this function does not source or validate it against any "
            "real market-data feed — QUANT_ENGINE_SPEC.md names no data "
            "source for this input",
        ],
        limitations=[
            "bounded to [0, 100] per QUANT_ENGINE_SPEC.md Section 9; a "
            "negative achieved_yield_on_cash is floored at 0 rather than "
            "reported as a negative score, which the spec's own formula "
            "does not itself state",
        ],
        dependencies=[],
    )


# --- Debt efficiency (QUANT_ENGINE_SPEC.md Section 7 — DESIGNED, no spec formula) ---

# DESIGNED, not spec-derived. QUANT_ENGINE_SPEC.md Section 7 describes
# Debt efficiency only in prose — "penalised proportionally to the gap
# between effective borrowing cost and the risk-adjusted expected return
# available on capital that could otherwise repay that debt" — with no
# formula. This constant and `debt_efficiency` below are an engineering
# decision filling that gap.
#
# _DEBT_EFFICIENCY_FULL_SWING_GAP: the return-vs-cost gap (in the same
# decimal units as both inputs, e.g. 0.10 = 10 percentage points) at
# which the score saturates to 100 (return exceeds cost by this much) or
# 0 (cost exceeds return by this much). 10 percentage points was chosen
# as a round, illustrative magnitude comfortably larger than typical
# real borrowing-cost/expected-return spreads — an explicit calibration
# placeholder (QUANT_ENGINE_SPEC.md Section 11 item 1), not a fitted or
# sourced value.
_DEBT_EFFICIENCY_FULL_SWING_GAP = 0.10


def debt_efficiency(
    effective_borrowing_cost: float,
    risk_adjusted_expected_return: float,
) -> UAP:
    """
    Debt efficiency — DESIGNED, not a QUANT_ENGINE_SPEC.md formula.
    Section 7 gives this sub-score in prose only, with no equation; see
    the module docstring and `_DEBT_EFFICIENCY_FULL_SWING_GAP`'s comment
    above for why and how this specific formula was chosen.

    Debt is efficient (score > 50) when the risk-adjusted expected
    return available on capital exceeds the effective cost of the debt
    that capital could otherwise repay — capital is better deployed than
    used to pay down debt. Debt is inefficient (score < 50) when
    borrowing cost exceeds that return. Breakeven — return exactly
    equals cost — is exactly 50, by construction, scaling symmetrically
    around that midpoint and clamped to [0, 100].
    """
    gap = risk_adjusted_expected_return - effective_borrowing_cost
    raw_score = 50.0 + (gap / _DEBT_EFFICIENCY_FULL_SWING_GAP) * 50.0
    score = _clamp_score(raw_score)

    return UAP(
        subject="Debt efficiency sub-score",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=score,
        source="computed from provided effective_borrowing_cost, risk_adjusted_expected_return",
        producer=(
            "quant-engine / Debt efficiency (DESIGNED — no "
            "QUANT_ENGINE_SPEC.md formula; see docstring), "
            "QUANT_ENGINE_SPEC.md Section 7"
        ),
        # LOW, not MODERATE: unlike the four spec-derived sub-scores,
        # this formula's STRUCTURE — not just its constants — is an
        # engineering decision QUANT_ENGINE_SPEC.md never specified.
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "effective_borrowing_cost and risk_adjusted_expected_return "
            "are expressed over the same period and in consistent units",
            f"a gap of +/-{_DEBT_EFFICIENCY_FULL_SWING_GAP} (same units as "
            "both inputs) saturates the score to 100/0 — an explicit "
            "calibration placeholder not present anywhere in "
            "QUANT_ENGINE_SPEC.md",
        ],
        limitations=[
            "this sub-score's formula (linear, symmetric around a "
            "50-point breakeven) is a DESIGNED placeholder filling a gap "
            "QUANT_ENGINE_SPEC.md Section 7 leaves as prose only, with no "
            "equation — not a transcription of spec content",
        ],
        dependencies=[],
    )


# --- Risk efficiency (QUANT_ENGINE_SPEC.md Section 7 — spec-derived) ---


def risk_efficiency(
    portfolio_value: float,
    portfolio_std_dev: float,
    confidence_level: float,
    target_risk: float,
) -> UAP:
    """
    Risk efficiency (QUANT_ENGINE_SPEC.md Section 7, exact formula):

        100 - (|realised_risk - target_risk| / target_risk) x 100, floored at 0

    A deviation-from-target-band approach, using the Mandate's stated
    risk tolerance (`DATA_ARCHITECTURE.md` Section 4.1) as the target.

    `realised_risk` is computed here via `parametric_var` (this
    package's own risk function), per this task's explicit instruction
    to use it "for consistency with how risk is measured everywhere else
    in this project (the loss cap)" — rather than accepting
    realised_risk as an arbitrary caller-supplied float.

    `target_risk` is assumed to be supplied in the same units as
    `parametric_var`'s result (a portfolio-value-scaled loss magnitude),
    since the formula directly differences the two — QUANT_ENGINE_SPEC.md
    does not itself pin down target_risk's exact representation beyond
    naming it as the Mandate's risk tolerance.
    """
    _require_nonzero_denominator(target_risk, "target_risk", "risk_efficiency")

    realised_risk_uap = parametric_var(
        portfolio_value=portfolio_value,
        portfolio_std_dev=portfolio_std_dev,
        confidence_level=confidence_level,
    )
    realised_risk = realised_risk_uap.result

    raw_score = 100.0 - (abs(realised_risk - target_risk) / target_risk) * 100.0
    score = _clamp_score(raw_score)

    return UAP(
        subject="Risk efficiency sub-score",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=score,
        source="computed from parametric VaR (realised_risk) and the provided target_risk",
        producer="quant-engine / Risk efficiency, QUANT_ENGINE_SPEC.md Section 7",
        # LOW: inherits parametric_var's own LOW confidence (the
        # normal-distribution assumption), since realised_risk is
        # computed via it.
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "target_risk is expressed in the same units as "
            "parametric_var's result (a portfolio-value-scaled loss "
            "magnitude), and represents the Mandate's stated risk "
            "tolerance (DATA_ARCHITECTURE.md Section 4.1)",
            "portfolio returns are normally distributed (inherited from "
            "parametric_var, QUANT_ENGINE_SPEC.md Section 5.3)",
        ],
        limitations=[
            "inherits parametric VaR's understatement of tail risk for "
            "fatter-tailed real return distributions",
            "floored at 0 per QUANT_ENGINE_SPEC.md Section 7's explicit "
            "statement; also capped at 100 per Section 9's separate "
            "blanket bound, which Section 7's own prose does not restate",
        ],
        dependencies=[realised_risk_uap.id],
    )


# --- Tax efficiency (QUANT_ENGINE_SPEC.md Section 7 — spec-derived) ---


def tax_efficiency(
    tax_advantaged_allocation_used: float,
    tax_advantaged_allocation_available: float,
) -> UAP:
    """
    Tax efficiency (QUANT_ENGINE_SPEC.md Section 7, exact formula):

        (tax_advantaged_allocation_used / tax_advantaged_allocation_available) x 100

    Utilisation of ISA/pension-style allowances (Tier 1,
    `PRODUCT_VISION.md` Section 6).
    """
    _require_nonzero_denominator(
        tax_advantaged_allocation_available, "tax_advantaged_allocation_available", "tax_efficiency"
    )

    raw_score = (tax_advantaged_allocation_used / tax_advantaged_allocation_available) * 100.0
    score = _clamp_score(raw_score)

    return UAP(
        subject="Tax efficiency sub-score",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=score,
        source="computed from provided tax_advantaged_allocation_used, tax_advantaged_allocation_available",
        producer="quant-engine / Tax efficiency, QUANT_ENGINE_SPEC.md Section 7",
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "tax_advantaged_allocation_used and _available are expressed "
            "in the same currency and as of the same point in time",
        ],
        limitations=[
            "bounded to [0, 100] per QUANT_ENGINE_SPEC.md Section 9; the "
            "spec's own formula states no explicit ceiling, so a "
            "used > available input (which should not occur if inputs "
            "are internally consistent) is clamped rather than reported "
            "over 100",
        ],
        dependencies=[],
    )


# --- Liquidity efficiency (QUANT_ENGINE_SPEC.md Section 7 — DESIGNED, no spec formula) ---

# DESIGNED, not spec-derived, same status as Debt efficiency above.
# QUANT_ENGINE_SPEC.md Section 7 states only that this sub-score is
# "penalised for deviation from the Mandate's minimum cash reserve in
# either direction — whether shortfall and excess should be penalised
# symmetrically or asymmetrically is a calibration decision, not fixed
# here" — explicitly leaving the symmetry choice open (restated as an
# open question in Section 11 item 3).
#
# This implementation chooses ASYMMETRIC: falling below the minimum
# reserve is a liquidity-risk problem (the user may be unable to meet
# near-term obligations without forced, possibly disadvantageous, asset
# sales); holding cash above the minimum is only an opportunity-cost
# tradeoff (idle capital that could have been invested) — a materially
# less severe failure mode, so it is penalised more gently.
#
# _LIQUIDITY_SHORTFALL_PENALTY_RATE / _LIQUIDITY_EXCESS_PENALTY_RATE:
# score points lost per 100% relative deviation from the reserve, in
# each direction. Shortfall penalised 3x as steeply as excess — an
# illustrative, explicitly chosen ratio (QUANT_ENGINE_SPEC.md Section 11
# item 1 calibration placeholder), not a fitted or sourced value.
_LIQUIDITY_SHORTFALL_PENALTY_RATE = 300.0
_LIQUIDITY_EXCESS_PENALTY_RATE = 100.0


def liquidity_efficiency(
    actual_cash: float,
    minimum_cash_reserve: float,
) -> UAP:
    """
    Liquidity efficiency — DESIGNED, not a QUANT_ENGINE_SPEC.md formula.
    See the comment above `_LIQUIDITY_SHORTFALL_PENALTY_RATE` for why
    ASYMMETRIC penalisation was chosen (the spec leaves this choice
    explicitly open) and how the two rates were set.

    Score is 100 exactly when actual_cash == minimum_cash_reserve (the
    Mandate's stated minimum, `DATA_ARCHITECTURE.md` Section 4.1), and
    decreases with deviation in either direction — more steeply below
    the reserve than above it — floored at 0 and capped at 100.
    """
    _require_nonzero_denominator(minimum_cash_reserve, "minimum_cash_reserve", "liquidity_efficiency")

    deviation = actual_cash - minimum_cash_reserve
    relative_deviation = abs(deviation) / minimum_cash_reserve

    if deviation < 0:
        raw_score = 100.0 - relative_deviation * _LIQUIDITY_SHORTFALL_PENALTY_RATE
    else:
        raw_score = 100.0 - relative_deviation * _LIQUIDITY_EXCESS_PENALTY_RATE

    score = _clamp_score(raw_score)

    return UAP(
        subject="Liquidity efficiency sub-score",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=score,
        source="computed from provided actual_cash, minimum_cash_reserve",
        producer=(
            "quant-engine / Liquidity efficiency (DESIGNED — no "
            "QUANT_ENGINE_SPEC.md formula; see docstring), "
            "QUANT_ENGINE_SPEC.md Section 7"
        ),
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "actual_cash and minimum_cash_reserve are expressed in the "
            "same currency as of the same point in time",
            f"shortfall is penalised "
            f"{_LIQUIDITY_SHORTFALL_PENALTY_RATE / _LIQUIDITY_EXCESS_PENALTY_RATE:.0f}x "
            "as steeply as an equal-magnitude excess — an explicit "
            "calibration placeholder not present anywhere in "
            "QUANT_ENGINE_SPEC.md",
        ],
        limitations=[
            "this sub-score's formula (asymmetric penalty, 100 at exact "
            "reserve adherence) is a DESIGNED placeholder filling a gap "
            "QUANT_ENGINE_SPEC.md Section 7 leaves explicitly open — not "
            "a transcription of spec content; the spec itself states the "
            "symmetric-vs-asymmetric choice 'is a calibration decision, "
            "not fixed here'",
        ],
        dependencies=[],
    )


# --- Investment efficiency (QUANT_ENGINE_SPEC.md Section 7 — spec-derived) ---


def investment_efficiency(
    portfolio_return: float,
    risk_free_rate: float,
    portfolio_std_dev: float,
    max_achievable_sharpe_ratio: UAP,
) -> UAP:
    """
    Investment efficiency (QUANT_ENGINE_SPEC.md Section 7, exact
    formula): ratio of the portfolio's achieved Sharpe ratio (Section
    5.2) to the maximum Sharpe ratio achievable at the same risk level
    on `optimisation-engine`'s efficient frontier for the user's
    Mandate.

    `max_achievable_sharpe_ratio` is accepted as an already-computed
    `UAP` (not a raw float) precisely because Section 7 flags this
    sub-score as "explicitly dependent on optimisation-engine's output,
    which should be reflected in this packet's dependencies field" —
    its `.id` is recorded in the returned UAP's `dependencies` below.
    `optimisation-engine` does not yet implement Section 5.3's efficient
    frontier (confirmed not-yet-implemented future work in that
    package's own `__init__.py`) — this function does not attempt to
    compute that value itself; it must be supplied by the caller once
    that upstream capability exists, the same treatment this project
    gives every other not-yet-implemented upstream dependency.

    The portfolio's own achieved Sharpe ratio is computed here via
    `sharpe_ratio` (this package's own function), and its `.id` is also
    recorded in `dependencies`.
    """
    achieved_sharpe_uap = sharpe_ratio(
        portfolio_return=portfolio_return,
        risk_free_rate=risk_free_rate,
        portfolio_std_dev=portfolio_std_dev,
    )
    achieved_sharpe = achieved_sharpe_uap.result
    max_sharpe = max_achievable_sharpe_ratio.result

    _require_nonzero_denominator(
        max_sharpe, "max_achievable_sharpe_ratio.result", "investment_efficiency"
    )

    raw_score = (achieved_sharpe / max_sharpe) * 100.0
    score = _clamp_score(raw_score)

    return UAP(
        subject="Investment efficiency sub-score",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=score,
        source=(
            "computed from achieved Sharpe ratio and optimisation-"
            "engine's max-achievable-Sharpe-on-the-efficient-frontier"
        ),
        producer="quant-engine / Investment efficiency, QUANT_ENGINE_SPEC.md Section 7",
        # LOW: compounds two ESTIMATE-class uncertainties — the achieved
        # Sharpe ratio's own inputs, and optimisation-engine's not-yet-
        # implemented efficient-frontier computation this sub-score
        # depends on but cannot itself verify.
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "max_achievable_sharpe_ratio reflects the SAME risk level "
            "(portfolio_std_dev) as the achieved Sharpe ratio computed "
            "here, per QUANT_ENGINE_SPEC.md Section 7's 'at the same "
            "risk level' requirement — this function cannot itself "
            "verify that the caller supplied a frontier point at "
            "matching risk",
        ],
        limitations=[
            "depends on optimisation-engine's efficient-frontier "
            "computation, which is not yet implemented as code — "
            "max_achievable_sharpe_ratio must be supplied by the caller "
            "from elsewhere until it is",
            "a negative achieved Sharpe ratio produces a score bounded "
            "at 0 (via the shared clamp), not a signed ratio",
        ],
        dependencies=[achieved_sharpe_uap.id, max_achievable_sharpe_ratio.id],
    )


# --- The composite score (QUANT_ENGINE_SPEC.md Section 8) ---


def composite_capital_efficiency_score(
    cash_efficiency_uap: UAP,
    debt_efficiency_uap: UAP,
    risk_efficiency_uap: UAP,
    tax_efficiency_uap: UAP,
    liquidity_efficiency_uap: UAP,
    investment_efficiency_uap: UAP,
) -> UAP:
    """
    The composite Capital Efficiency Score (QUANT_ENGINE_SPEC.md Section
    8): aggregates the six sub-scores. Section 8 leaves the aggregation
    method open ("e.g. a weighted average, and what those weights are")
    — this function uses an EQUAL-weighted average (1/6 each), the only
    currently-justified default given Section 11 item 1's explicit
    deferral of real calibration to a later empirical step. This is a
    PROVISIONAL choice, not a spec-derived one — flagged both in this
    docstring and in the returned UAP's `assumptions` field.

    Section 9 requires every sub-score to already fall within [0, 100]
    "before the composite score is computed" — enforced here as an
    explicit precondition check (raises `ValueError` if violated), not
    merely assumed from each sub-score function's own clamping. The
    composite result is also explicitly re-clamped before being
    returned, as defense-in-depth.
    """
    sub_scores = {
        "cash_efficiency": cash_efficiency_uap,
        "debt_efficiency": debt_efficiency_uap,
        "risk_efficiency": risk_efficiency_uap,
        "tax_efficiency": tax_efficiency_uap,
        "liquidity_efficiency": liquidity_efficiency_uap,
        "investment_efficiency": investment_efficiency_uap,
    }

    for name, uap in sub_scores.items():
        if not (0.0 <= uap.result <= 100.0):
            raise ValueError(
                f"composite_capital_efficiency_score: {name}'s result "
                f"({uap.result!r}) is outside the [0, 100] bound "
                "QUANT_ENGINE_SPEC.md Section 9 requires every sub-score "
                "to satisfy before the composite is computed."
            )

    weight = 1.0 / 6.0
    composite = sum(uap.result * weight for uap in sub_scores.values())
    composite = _clamp_score(composite)

    return UAP(
        subject="Capital Efficiency Score (composite)",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=composite,
        source="computed from the six Capital Efficiency sub-scores",
        producer="quant-engine / Capital Efficiency Score (composite), QUANT_ENGINE_SPEC.md Section 8",
        # LOW: the weighting itself is an unvalidated placeholder, not
        # just ordinary input-accuracy uncertainty.
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "PROVISIONAL: equal weighting (1/6 per sub-score) is used "
            "because QUANT_ENGINE_SPEC.md Section 8 leaves the real "
            "aggregation method and weights open, deferred to a later "
            "empirical calibration step (Section 11 item 1) — this is "
            "not a spec-derived weighting and should not be read as one",
        ],
        limitations=[
            "two of the six sub-scores (debt_efficiency, "
            "liquidity_efficiency) are themselves DESIGNED placeholders, "
            "not QUANT_ENGINE_SPEC.md formulas — see their own "
            "docstrings",
        ],
        dependencies=[uap.id for uap in sub_scores.values()],
    )
