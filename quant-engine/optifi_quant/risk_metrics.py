"""
Risk and risk-adjusted performance metrics — QUANT_ENGINE_SPEC.md,
Sections 5.2 (Risk-Adjusted Performance Metrics) and 5.3 (Risk
Measurement).

Implements exactly three functions: `sharpe_ratio`, `historical_var`, and
`parametric_var`. No other metric from Section 5, and no Capital
Efficiency sub-score from Section 7/8, is implemented here — those remain
separate future work (Investment Efficiency in particular depends on
`optimisation-engine`'s efficient frontier, which does not exist as code
yet).

Every function applies the relevant guardrail from
QUANT_ENGINE_SPEC.md Section 9 ("Quantitative Validation") and returns its
result wrapped in a `UAP` with `information_class=ESTIMATE`.
"""

from __future__ import annotations

from scipy.stats import norm

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

# QUANT_ENGINE_SPEC.md Section 9: "Any ratio with a volatility denominator
# ... must guard against a zero or near-zero denominator." Chosen as a
# small absolute threshold rather than exactly zero, since floating-point
# volatility inputs derived from real calculations are unlikely to be
# exactly 0.0 even when they are, for practical purposes, degenerate.
_STD_DEV_EPSILON = 1e-9


def sharpe_ratio(
    portfolio_return: float,
    risk_free_rate: float,
    portfolio_std_dev: float,
) -> UAP:
    """
    Sharpe ratio (QUANT_ENGINE_SPEC.md, Section 5.2): (R_p - R_f) / sigma_p.

    Raises ValueError if `portfolio_std_dev` is zero or below
    `_STD_DEV_EPSILON` (Section 9's zero/near-zero denominator guard).
    """
    if abs(portfolio_std_dev) < _STD_DEV_EPSILON:
        raise ValueError(
            f"sharpe_ratio: portfolio_std_dev ({portfolio_std_dev!r}) is "
            f"zero or below the epsilon threshold ({_STD_DEV_EPSILON}); "
            "the Sharpe ratio is undefined for a (near-)zero-volatility "
            "portfolio (QUANT_ENGINE_SPEC.md Section 9)."
        )

    result = (portfolio_return - risk_free_rate) / portfolio_std_dev

    return UAP(
        subject="portfolio Sharpe ratio",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="computed from provided portfolio_return, risk_free_rate, portfolio_std_dev",
        producer="quant-engine / Sharpe ratio, QUANT_ENGINE_SPEC.md Section 5.2",
        # MODERATE: the formula itself is standard and deterministic (not
        # LOW), but this function has no way to verify the accuracy of the
        # caller-supplied inputs (not HIGH) — confidence in the formula's
        # correctness is high, confidence in the real-world result depends
        # on inputs this function can't itself corroborate.
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "portfolio_return, risk_free_rate, and portfolio_std_dev are "
            "expressed over the same period and consistently annualised "
            "(or consistently un-annualised) with one another",
        ],
        limitations=[
            "Sharpe ratio penalises upside and downside volatility "
            "equally; it does not distinguish harmful variance from "
            "beneficial variance",
        ],
        dependencies=[],
    )


def _percentile_linear(data: list[float], percentile: float) -> float:
    """
    Linear-interpolation percentile (matching numpy.percentile's default
    'linear' method), implemented without adding numpy as a dependency.
    `percentile` is 0-100.
    """
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]

    rank = (percentile / 100) * (n - 1)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, n - 1)
    fraction = rank - lower_index
    return sorted_data[lower_index] + fraction * (
        sorted_data[upper_index] - sorted_data[lower_index]
    )


def historical_var(returns: list[float], confidence_level: float) -> UAP:
    """
    Historical VaR (QUANT_ENGINE_SPEC.md, Section 5.3): the loss at the
    given percentile of the actual historical return distribution — no
    distributional assumption.

    `confidence_level` is e.g. 0.95 for a 95% VaR, i.e. the 5th percentile
    of the historical returns.

    Non-negative loss magnitude convention: VaR is reported as the
    magnitude of loss. If the percentile return itself is non-negative
    (the tail outcome at this confidence level is not actually a loss),
    this function reports VaR as 0.0 rather than `abs()`-ing a positive
    return into a fabricated "loss" of the same size — a gain is not a
    loss, so reporting it as one would misrepresent the risk. VaR is
    floored at 0.0, not reflected via absolute value, in either case.
    """
    if not returns:
        raise ValueError("historical_var: `returns` must be a non-empty list.")
    if not (0 < confidence_level < 1):
        raise ValueError(
            f"historical_var: confidence_level must be strictly between 0 "
            f"and 1, got {confidence_level!r}."
        )

    percentile = (1 - confidence_level) * 100
    percentile_return = _percentile_linear(returns, percentile)

    # Non-negative loss-magnitude guard (QUANT_ENGINE_SPEC.md Section 9) —
    # see the docstring above for the floor-at-zero convention.
    var = max(0.0, -percentile_return)

    return UAP(
        subject=f"historical VaR at {confidence_level:.0%} confidence",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=var,
        source="computed from the provided historical returns sample",
        producer="quant-engine / historical VaR, QUANT_ENGINE_SPEC.md Section 5.3",
        # MODERATE: makes no distributional assumption (more robust than
        # parametric VaR in that respect), but its accuracy depends
        # entirely on the historical sample being representative of
        # future conditions, which this function cannot verify from the
        # data alone.
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "the provided returns are expressed over consistent periods "
            "and are drawn from the same portfolio/instrument",
        ],
        limitations=[
            "historical VaR assumes the historical sample is "
            "representative of future return behaviour; it cannot "
            "anticipate a regime change or an event with no precedent in "
            "the sample",
        ],
        dependencies=[],
    )


def parametric_var(
    portfolio_value: float,
    portfolio_std_dev: float,
    confidence_level: float,
) -> UAP:
    """
    Parametric (variance-covariance) VaR (QUANT_ENGINE_SPEC.md,
    Section 5.3): VaR = Z_alpha * sigma_p * portfolio_value, assuming
    normally distributed returns. `Z_alpha` is derived from
    `confidence_level` via `scipy.stats.norm.ppf` — not a hard-coded
    lookup table.

    Same non-negative loss-magnitude convention as `historical_var`: the
    result is floored at 0.0.
    """
    if not (0 < confidence_level < 1):
        raise ValueError(
            f"parametric_var: confidence_level must be strictly between 0 "
            f"and 1, got {confidence_level!r}."
        )

    z_alpha = norm.ppf(confidence_level)
    result = max(0.0, z_alpha * portfolio_std_dev * portfolio_value)

    return UAP(
        subject=f"parametric VaR at {confidence_level:.0%} confidence",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="computed from provided portfolio_value, portfolio_std_dev, confidence_level",
        producer="quant-engine / parametric VaR, QUANT_ENGINE_SPEC.md Section 5.3",
        # LOW: strictly weaker than historical VaR's MODERATE — this
        # method carries the same sample/estimation dependency as any
        # sigma-based measure, plus an additional, often-violated
        # assumption (normally distributed returns; real markets exhibit
        # fatter tails than a normal distribution predicts).
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "portfolio returns are normally distributed",
            "portfolio_std_dev and portfolio_value are expressed over the "
            "same period and in consistent units",
        ],
        limitations=[
            "the normal-distribution assumption understates tail risk "
            "for return distributions with fatter tails than normal, "
            "which is common for real financial returns",
        ],
        dependencies=[],
    )
