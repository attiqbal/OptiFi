"""
Independent checks on optimisation-engine's defined-risk options
structure candidates — HEDGING_SPEC.md Section 7's proposed
verification-engine role: "re-derive the proposed structure's hedge
ratio and maximum-loss bound independently... never calling
optimisation-engine's own generation logic — the same independence
verify_loss_cap_candidate already achieves." VERIFICATION_FRAMEWORK.md
Section 5.5's principle, applied to this new domain.

Neither function here imports `optifi_optimisation` or calls
`protective_put`/`collar` — the payoff formulas (HEDGING_SPEC.md Section
5.1/5.2) are reimplemented directly from raw inputs, mirroring
`optimisation_checks.py`'s own `verify_optimisation_candidate` pattern
(which likewise reimplements the weight-sum/bounds/target-return checks
rather than calling `minimize_variance`), not an echo of the candidate's
own reported figures.
"""

from __future__ import annotations

from optifi_shared import UAP

from .verdict import FailureCategory, Verdict, VerdictType


def _reject_malformed_shape(candidate_result: object, required_keys: set[str], fn_name: str) -> Verdict | None:
    if not isinstance(candidate_result, dict) or not required_keys.issubset(candidate_result.keys()):
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=[
                f"{fn_name}: candidate.result does not contain a usable "
                f"payoff structure (expected keys {sorted(required_keys)}, "
                f"got {candidate_result!r})"
            ],
            failure_category=FailureCategory.DATA_QUALITY,
        )
    return None


def verify_protective_put(
    candidate: UAP,
    position_quantity: float,
    current_price: float,
    put_strike: float,
    put_premium: float,
    tolerance: float = 1e-6,
) -> Verdict:
    """
    Independently re-derive `protective_put`'s reported `max_loss` and
    `breakeven_price` (HEDGING_SPEC.md Section 5.1) from raw inputs, and
    confirm they match the candidate's reported figures. Mismatch ->
    REJECT, naming the specific discrepancy.
    """
    malformed = _reject_malformed_shape(
        candidate.result, {"max_loss", "breakeven_price"}, "verify_protective_put"
    )
    if malformed is not None:
        return malformed

    expected_max_loss = ((current_price - put_strike) + put_premium) * position_quantity
    expected_breakeven = current_price + put_premium

    reasons: list[str] = []
    reported_max_loss = candidate.result["max_loss"]
    if abs(reported_max_loss - expected_max_loss) > tolerance:
        reasons.append(
            f"candidate's reported max_loss ({reported_max_loss!r}) does "
            f"not match independently recomputed max_loss "
            f"({expected_max_loss!r}) from raw inputs (current_price="
            f"{current_price!r}, put_strike={put_strike!r}, put_premium="
            f"{put_premium!r}, position_quantity={position_quantity!r})"
        )

    reported_breakeven = candidate.result["breakeven_price"]
    if abs(reported_breakeven - expected_breakeven) > tolerance:
        reasons.append(
            f"candidate's reported breakeven_price ({reported_breakeven!r}) "
            f"does not match independently recomputed breakeven_price "
            f"({expected_breakeven!r}) from raw inputs (current_price="
            f"{current_price!r}, put_premium={put_premium!r})"
        )

    if reasons:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=reasons,
            failure_category=FailureCategory.DATA_QUALITY,
        )
    return Verdict(
        verdict_type=VerdictType.PASS,
        reasons=[
            "independently recomputed max_loss and breakeven_price match "
            "the candidate's reported figures"
        ],
    )


def verify_collar(
    candidate: UAP,
    position_quantity: float,
    current_price: float,
    put_strike: float,
    put_premium: float,
    call_strike: float,
    call_premium: float,
    call_covered_quantity: float,
    tolerance: float = 1e-6,
) -> Verdict:
    """
    Independently re-derive `collar`'s reported `floor_price`/
    `ceiling_price`/`max_loss`/`max_gain` (HEDGING_SPEC.md Section 5.2)
    from raw inputs, and confirm they match the candidate's reported
    figures.

    Also independently RE-DERIVES the naked-call constraint
    (HEDGING_SPEC.md Section 6) from the raw `call_covered_quantity` /
    `position_quantity` inputs themselves -- genuine defense-in-depth,
    not a re-read of whatever `optimisation-engine`'s `collar()` already
    concluded. If `call_covered_quantity > position_quantity` is true of
    the RAW inputs, that is REJECTed here regardless of what the
    candidate's own `result` claims -- this should never legitimately
    happen (optimisation-engine's own structural guard should have
    already refused to construct such a candidate at all), so reaching
    this state at all is itself worth a clearly-worded reason: it means
    that guard was somehow bypassed.

    A genuine PARTIAL collar (`call_covered_quantity < position_quantity`,
    which IS legitimately allowed by `collar()`) is not a rejection --
    but leaves real, uncapped residual exposure on the uncollared
    portion, which is a genuine borderline case: the candidate's figures
    are correct and the structure is legitimate, but a caveat belongs
    downstream (VERIFICATION_FRAMEWORK.md Section 4: "output stands, but
    a caveat is attached") -- PASS WITH CAUTION, naming the specific
    uncovered quantity. A fully-covered collar with matching figures is a
    clean PASS.
    """
    required_keys = {
        "floor_price",
        "ceiling_price",
        "net_premium_per_share",
        "max_loss",
        "max_gain",
        "collared_quantity",
        "uncollared_quantity",
    }
    malformed = _reject_malformed_shape(candidate.result, required_keys, "verify_collar")
    if malformed is not None:
        return malformed

    # THE independent re-derivation of the naked-call constraint --
    # checked from the RAW inputs, first, before anything else.
    if call_covered_quantity > position_quantity:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=[
                f"call_covered_quantity ({call_covered_quantity!r}) "
                f"exceeds position_quantity ({position_quantity!r}), "
                "independently re-derived from raw inputs -- a partially "
                "or wholly naked/uncovered call with unbounded loss "
                "potential (HEDGING_SPEC.md Section 6). This candidate "
                "should never have reached independent verification in "
                "this state; optimisation-engine's own structural guard "
                "(collar()'s call_covered_quantity check) appears to have "
                "been bypassed."
            ],
            failure_category=FailureCategory.DATA_QUALITY,
        )

    expected_net_premium = put_premium - call_premium
    expected_max_loss = ((current_price - put_strike) + expected_net_premium) * call_covered_quantity
    expected_max_gain = ((call_strike - current_price) - expected_net_premium) * call_covered_quantity
    expected_uncollared_quantity = position_quantity - call_covered_quantity

    reasons: list[str] = []
    checks = [
        ("floor_price", put_strike),
        ("ceiling_price", call_strike),
        ("net_premium_per_share", expected_net_premium),
        ("max_loss", expected_max_loss),
        ("max_gain", expected_max_gain),
        ("collared_quantity", call_covered_quantity),
        ("uncollared_quantity", expected_uncollared_quantity),
    ]
    for field_name, expected_value in checks:
        reported_value = candidate.result[field_name]
        if abs(reported_value - expected_value) > tolerance:
            reasons.append(
                f"candidate's reported {field_name} ({reported_value!r}) "
                f"does not match independently recomputed {field_name} "
                f"({expected_value!r})"
            )

    if reasons:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=reasons,
            failure_category=FailureCategory.DATA_QUALITY,
        )

    if expected_uncollared_quantity > tolerance:
        return Verdict(
            verdict_type=VerdictType.PASS_WITH_CAUTION,
            reasons=[
                "independently recomputed figures match the candidate's "
                f"reported figures, but this is a PARTIAL collar: only "
                f"{call_covered_quantity!r} of {position_quantity!r} held "
                f"units are collared, leaving {expected_uncollared_quantity!r} "
                "units with uncapped, unhedged exposure -- neither the "
                "floor nor the ceiling applies to the uncollared portion"
            ],
        )

    return Verdict(
        verdict_type=VerdictType.PASS,
        reasons=[
            "independently recomputed floor_price, ceiling_price, "
            "max_loss, and max_gain match the candidate's reported "
            "figures, and the full position is collared (no uncovered "
            "residual exposure)"
        ],
    )
