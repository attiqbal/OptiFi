"""
Minimum-variance hedge ratio — HEDGING_SPEC.md Section 4.1.

    h* = Cov(delta_S, delta_F) / Var(delta_F)

Structurally the same formula as QUANT_ENGINE_SPEC.md Section 5.3's Beta
(`beta = Cov(R_p, R_m) / Var(R_m)`), reusing this package's own Section
5.5 machinery directly (`covariance_matrix`) rather than reimplementing
pairwise covariance/variance — HEDGING_SPEC.md Section 4.1 states this
explicitly: "no new statistical methodology is introduced by hedge ratio
calculation itself, only a new application of existing ones."

Only the minimum-variance hedge ratio and hedge effectiveness (R^2) are
implemented here — HEDGING_SPEC.md Section 4.3's dynamic-hedging
rebalancing cadence is an explicitly open question (not addressed by this
module, which computes a single, static estimate from the provided
sample), and options-based structures (Section 5/6 of that document) are
a separate, not-yet-implemented capability.
"""

from __future__ import annotations

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

from .covariance import covariance_matrix

# A genuine sample standard deviation of exactly (or near) zero means a
# constant return series -- for the hedge instrument, this makes h*
# (division by Var(F)) undefined; for the position, it makes R^2
# (division by Var(S) as well as Var(F)) undefined. Same value and same
# reasoning as covariance.py's own _STD_DEV_EPSILON: a tolerance for
# floating-point noise around a genuinely-zero variance, not a relaxation
# of the requirement that both series carry real variation.
_STD_DEV_EPSILON = 1e-12


def minimum_variance_hedge_ratio(
    position_returns: list[float],
    hedge_instrument_returns: list[float],
) -> UAP:
    """
    Minimum-variance hedge ratio (HEDGING_SPEC.md Section 4.1):

        h* = Cov(delta_S, delta_F) / Var(delta_F)

    minimizing Var(delta_S - h * delta_F) -- the variance of the *hedged*
    position's value change -- over choices of h.

    A single `covariance_matrix` call over {"position": position_returns,
    "hedge_instrument": hedge_instrument_returns} yields Cov(S,S)
    (=Var(S)), Cov(S,F), and Cov(F,F) (=Var(F)) all at once; h* and hedge
    effectiveness R^2 = Cov(S,F)^2 / (Var(S)*Var(F)) = correlation(S,F)^2
    (HEDGING_SPEC.md Section 4.1) are both derived directly from that one
    matrix, not recomputed independently.

    Raises ValueError if either series has zero or near-zero variance --
    a constant hedge_instrument_returns series makes h* undefined
    (division by Var(F)=0); a constant position_returns series makes R^2
    undefined too (division by Var(S)=0 as well).
    """
    cov_uap = covariance_matrix(
        {"position": position_returns, "hedge_instrument": hedge_instrument_returns}
    )
    matrix = cov_uap.result

    var_position = matrix["position"]["position"]
    var_hedge_instrument = matrix["hedge_instrument"]["hedge_instrument"]
    cov_position_hedge = matrix["position"]["hedge_instrument"]

    if var_hedge_instrument**0.5 < _STD_DEV_EPSILON:
        raise ValueError(
            "minimum_variance_hedge_ratio: hedge_instrument_returns has "
            f"zero or near-zero variance ({var_hedge_instrument!r}); the "
            "hedge ratio (Cov(S,F)/Var(F)) is undefined for a constant "
            "hedge instrument series."
        )
    if var_position**0.5 < _STD_DEV_EPSILON:
        raise ValueError(
            "minimum_variance_hedge_ratio: position_returns has zero or "
            f"near-zero variance ({var_position!r}); hedge effectiveness "
            "(R^2 = Cov(S,F)^2 / (Var(S)*Var(F))) is undefined when there "
            "is no position variance to explain."
        )

    hedge_ratio = cov_position_hedge / var_hedge_instrument
    hedge_effectiveness_r_squared = (cov_position_hedge**2) / (var_position * var_hedge_instrument)

    return UAP(
        subject="minimum-variance hedge ratio",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "hedge_ratio": hedge_ratio,
            "hedge_effectiveness_r_squared": hedge_effectiveness_r_squared,
        },
        source="computed from the provided position and hedge instrument return series",
        producer="quant-engine / minimum-variance hedge ratio, HEDGING_SPEC.md Section 4.1",
        # MODERATE: the formula itself is standard and deterministic (not
        # LOW), but this function has no way to verify the two return
        # series are actually representative of future behaviour (not
        # HIGH) -- the same reasoning covariance_matrix's own confidence
        # already applies, inherited here since this reuses that function.
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "position_returns and hedge_instrument_returns cover the "
            "same, aligned time periods and are expressed in consistent "
            "units",
            "h* is a static, single-sample estimate -- it does not "
            "account for how the ratio may decay over time "
            "(HEDGING_SPEC.md Section 4.3, an explicitly open question "
            "not addressed by this function)",
        ],
        limitations=[
            "a low hedge_effectiveness_r_squared means the hedge "
            "instrument explains little of the position's variance "
            "(HEDGING_SPEC.md Section 4.2's basis risk) -- this function "
            "reports that honestly rather than only returning h* for "
            "well-matched instrument pairs",
            "inherits covariance_matrix's own sample-size sensitivity "
            "and lack of estimation-error adjustment",
        ],
        dependencies=[cov_uap.id],
    )
