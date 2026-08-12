"""
Defined-risk options structures — HEDGING_SPEC.md Section 5 (protective
put, Section 5.1; collar, Section 5.2) and Section 6 (the naked/uncovered
options prohibition).

Scope boundary, deliberately narrow: this module computes each
structure's PAYOFF/RISK PROFILE (max loss, max gain, breakeven, bounded
range) from caller-supplied `current_price`, strike(s), and premium(s).
It does **not** price options — HEDGING_SPEC.md Section 5.3 names implied
volatility, strike selection, and expiry as required pricing inputs with
no data source specified anywhere in this project (Section 9, item 1 of
that document leaves this genuinely open, same treatment as Cash
efficiency's `best_available_comparable_yield`,
`QUANT_ENGINE_SPEC.md` Section 7), and Section 9, item 6 separately
leaves the pricing MODEL itself (Black-Scholes, binomial, or otherwise)
unresolved. Implementing either would resolve an open question this
document explicitly does not resolve, so this module treats premium,
strike, and expiry purely as caller-supplied numbers, never derived.

The naked/uncovered options prohibition (HEDGING_SPEC.md Section 6) is
enforced here structurally, not as a downstream check — see `collar`'s
`call_covered_quantity` guard below, modeled directly on
`mean_variance.py`'s `minimize_variance_with_loss_cap` loss-cap
precedent: a candidate that would breach the constraint is rejected
before a `UAP` is ever constructed, not generated and then flagged.
"""

from __future__ import annotations

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus


def _validate_position_and_pricing_inputs(
    fn_name: str,
    position_quantity: float,
    current_price: float,
    **strikes_and_premiums: float,
) -> None:
    if position_quantity <= 0:
        raise ValueError(
            f"{fn_name}: position_quantity must be positive, got "
            f"{position_quantity!r}."
        )
    if current_price <= 0:
        raise ValueError(
            f"{fn_name}: current_price must be positive, got {current_price!r}."
        )
    for name, value in strikes_and_premiums.items():
        if "strike" in name and value <= 0:
            raise ValueError(f"{fn_name}: {name} must be positive, got {value!r}.")
        if "premium" in name and value < 0:
            raise ValueError(f"{fn_name}: {name} must be non-negative, got {value!r}.")


def protective_put(
    position_quantity: float,
    current_price: float,
    put_strike: float,
    put_premium: float,
) -> UAP:
    """
    Protective put payoff structure (HEDGING_SPEC.md Section 5.1): hold
    `position_quantity` of the underlying, and buy a put at `put_strike`
    for `put_premium` per share.

    Maximum loss (Section 5.1's own formula, exactly): per-share
    `(current_price - put_strike) + put_premium`, scaled by
    `position_quantity` -- a fixed, pre-computable number regardless of
    how far the underlying subsequently falls below the strike.

    Breakeven: `current_price + put_premium` -- the price the underlying
    must reach for the position's P&L (net of the premium already paid)
    to reach zero.

    Upside is explicitly reported as NOT capped: above the strike, the
    put simply expires worthless and P&L tracks the underlying 1:1, minus
    the fixed premium drag -- there is no numeric "maximum gain" to
    report, unlike the collar below, which trades away unlimited upside
    for a lower (or zero) net cost.

    No naked-position sizing constraint applies here (unlike `collar`'s
    `call_covered_quantity` guard): a LONG put's maximum loss is always
    the premium paid, bounded regardless of how it compares to
    `position_quantity` -- HEDGING_SPEC.md Section 6's prohibition is
    specifically about SOLD/short positions without cover, not purchased
    protection of any size.
    """
    _validate_position_and_pricing_inputs(
        "protective_put",
        position_quantity,
        current_price,
        put_strike=put_strike,
        put_premium=put_premium,
    )

    max_loss_per_share = (current_price - put_strike) + put_premium
    max_loss = max_loss_per_share * position_quantity
    breakeven_price = current_price + put_premium

    return UAP(
        subject="protective put payoff structure",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "max_loss": max_loss,
            "breakeven_price": breakeven_price,
            "upside_capped": False,
        },
        source="computed from the provided position, put strike, and put premium",
        producer="optimisation-engine / protective put, HEDGING_SPEC.md Section 5.1",
        # MODERATE: the payoff arithmetic is exact given the inputs, but
        # this function cannot itself verify put_strike/put_premium are
        # real, currently-available market prices (it doesn't price
        # options -- see the module docstring).
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "put_strike and put_premium are caller-supplied, real market "
            "figures for a genuinely available put option -- this "
            "function does not price options itself (HEDGING_SPEC.md "
            "Section 5.3/Section 9 item 6: the pricing model is an "
            "explicitly open, unresolved question)",
            "the put is held to expiry rather than closed out early",
        ],
        limitations=[
            "upside above put_strike is unlimited, reduced by the fixed "
            "put_premium cost -- not a numeric bound, see "
            "upside_capped=False above",
            "expiry/time-to-expiration is not modeled -- this is a "
            "static payoff-at-expiry structure, not a live position "
            "valuation",
        ],
        dependencies=[],
    )


def collar(
    position_quantity: float,
    current_price: float,
    put_strike: float,
    put_premium: float,
    call_strike: float,
    call_premium: float,
    call_covered_quantity: float,
) -> UAP:
    """
    Collar payoff structure (HEDGING_SPEC.md Section 5.2): hold
    `position_quantity` of the underlying, buy a put at `put_strike` for
    `put_premium` (the floor), and sell a call at `call_strike` for
    `call_premium` (the ceiling) covering `call_covered_quantity` of the
    held position.

    THE STRUCTURAL NAKED-CALL REJECTION (HEDGING_SPEC.md Section 6): this
    is the first concrete application of that section's principle --
    `call_covered_quantity` must not exceed `position_quantity`. A call
    sized beyond what the held position actually covers is, by
    definition, partially or wholly an UNCOVERED (naked) call -- unlimited
    loss potential above the strike. Per Section 6: "must be structurally
    impossible for this system to generate. Not flagged after the fact.
    Not rejected downstream." This function raises `ValueError` and never
    constructs a `UAP` when this is violated -- modeled directly on
    `minimize_variance_with_loss_cap`'s loss-cap precedent
    (`OPTIMISATION_ENGINE_SPEC.md` Section 5.1a), which the same section
    of HEDGING_SPEC.md cites as its own precedent.

    `call_covered_quantity` may be LESS than `position_quantity` (a
    partial collar -- only part of the position is capped/floored; the
    remainder's own payoff is not computed here, only its size is
    reported as `uncollared_quantity`). It may never exceed it.

    Requires `call_strike > put_strike` -- a collar whose ceiling sits at
    or below its own floor bounds nothing sensible.

    On the collared quantity: maximum loss (per share)
    `= (current_price - put_strike) + net_premium`, maximum gain (per
    share) `= (call_strike - current_price) - net_premium`, where
    `net_premium = put_premium - call_premium` (positive = net cost,
    negative = net credit -- "typically low-cost" per Section 5.2, not
    guaranteed).
    """
    _validate_position_and_pricing_inputs(
        "collar",
        position_quantity,
        current_price,
        put_strike=put_strike,
        put_premium=put_premium,
        call_strike=call_strike,
        call_premium=call_premium,
    )
    if call_strike <= put_strike:
        raise ValueError(
            f"collar: call_strike ({call_strike!r}) must exceed put_strike "
            f"({put_strike!r}) -- a collar's ceiling must sit above its "
            "own floor."
        )
    if call_covered_quantity <= 0:
        raise ValueError(
            f"collar: call_covered_quantity must be positive, got "
            f"{call_covered_quantity!r}."
        )
    # THE structural naked-call rejection -- see docstring above and
    # HEDGING_SPEC.md Section 6. This must remain a hard raise, never
    # softened into a warning or a clamp: silently capping
    # call_covered_quantity down to position_quantity would hide the
    # caller's error rather than making the unsafe structure impossible
    # to produce.
    if call_covered_quantity > position_quantity:
        raise ValueError(
            f"collar: call_covered_quantity ({call_covered_quantity!r}) "
            f"exceeds position_quantity ({position_quantity!r}) -- this "
            "would sell a call not fully covered by the held position, "
            "i.e. a partially naked/uncovered call with unbounded loss "
            "potential above the strike. HEDGING_SPEC.md Section 6: any "
            "such position must be structurally impossible to generate, "
            "not generated and then flagged. Reduce call_covered_quantity "
            "to at most position_quantity."
        )

    net_premium = put_premium - call_premium
    max_loss_per_share = (current_price - put_strike) + net_premium
    max_gain_per_share = (call_strike - current_price) - net_premium

    return UAP(
        subject="collar payoff structure",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result={
            "floor_price": put_strike,
            "ceiling_price": call_strike,
            "net_premium_per_share": net_premium,
            "max_loss": max_loss_per_share * call_covered_quantity,
            "max_gain": max_gain_per_share * call_covered_quantity,
            "collared_quantity": call_covered_quantity,
            "uncollared_quantity": position_quantity - call_covered_quantity,
        },
        source=(
            "computed from the provided position, put strike/premium, "
            "and call strike/premium"
        ),
        producer="optimisation-engine / collar, HEDGING_SPEC.md Section 5.2",
        confidence=ConfidenceLevel.MODERATE,
        assumptions=[
            "put_strike, put_premium, call_strike, and call_premium are "
            "caller-supplied, real market figures for genuinely available "
            "options -- this function does not price options itself "
            "(HEDGING_SPEC.md Section 5.3/Section 9 item 6)",
            "both legs are held to expiry rather than closed out early",
        ],
        limitations=[
            "the payoff bounds (max_loss/max_gain) apply only to "
            "collared_quantity; uncollared_quantity's own payoff is not "
            "computed here, only its size is reported",
            "expiry/time-to-expiration is not modeled -- this is a "
            "static payoff-at-expiry structure, not a live position "
            "valuation",
        ],
        dependencies=[],
    )
