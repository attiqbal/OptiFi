"""
Tests for protective_put and collar (HEDGING_SPEC.md Section 5.1/5.2)
and the naked-call structural rejection (Section 6).
"""

import pytest

from optifi_optimisation import collar, protective_put


# --- protective_put ---


def test_protective_put_normal_case():
    # max_loss/share = (50-45)+2 = 7 -> 700 total; breakeven = 50+2 = 52
    uap = protective_put(
        position_quantity=100, current_price=50.0, put_strike=45.0, put_premium=2.0
    )
    assert uap.result["max_loss"] == pytest.approx(700.0)
    assert uap.result["breakeven_price"] == pytest.approx(52.0)
    assert uap.result["upside_capped"] is False


def test_protective_put_upside_is_reported_uncapped():
    uap = protective_put(
        position_quantity=1, current_price=100.0, put_strike=90.0, put_premium=3.0
    )
    assert uap.result["upside_capped"] is False


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(position_quantity=0, current_price=50.0, put_strike=45.0, put_premium=2.0),
        dict(position_quantity=-10, current_price=50.0, put_strike=45.0, put_premium=2.0),
        dict(position_quantity=100, current_price=0.0, put_strike=45.0, put_premium=2.0),
        dict(position_quantity=100, current_price=50.0, put_strike=0.0, put_premium=2.0),
        dict(position_quantity=100, current_price=50.0, put_strike=45.0, put_premium=-1.0),
    ],
)
def test_protective_put_rejects_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        protective_put(**kwargs)


# --- collar ---


def test_collar_normal_case_fully_covered():
    # net_premium = 2 - 1.5 = 0.5
    # max_loss/share = (50-45)+0.5 = 5.5 -> 550; max_gain/share = (55-50)-0.5 = 4.5 -> 450
    uap = collar(
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=100,
    )
    result = uap.result
    assert result["floor_price"] == pytest.approx(45.0)
    assert result["ceiling_price"] == pytest.approx(55.0)
    assert result["net_premium_per_share"] == pytest.approx(0.5)
    assert result["max_loss"] == pytest.approx(550.0)
    assert result["max_gain"] == pytest.approx(450.0)
    assert result["collared_quantity"] == 100
    assert result["uncollared_quantity"] == 0


def test_collar_partial_coverage_is_allowed_and_reported():
    uap = collar(
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=60,
    )
    result = uap.result
    assert result["collared_quantity"] == 60
    assert result["uncollared_quantity"] == 40
    # Bounds scale with the collared quantity only.
    assert result["max_loss"] == pytest.approx(5.5 * 60)
    assert result["max_gain"] == pytest.approx(4.5 * 60)


def test_collar_net_credit_when_call_premium_exceeds_put_premium():
    uap = collar(
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=1.0,
        call_strike=55.0,
        call_premium=2.0,
        call_covered_quantity=100,
    )
    assert uap.result["net_premium_per_share"] == pytest.approx(-1.0)


def test_collar_requires_call_strike_above_put_strike():
    with pytest.raises(ValueError, match="must exceed put_strike"):
        collar(
            position_quantity=100,
            current_price=50.0,
            put_strike=55.0,  # inverted: put above call
            put_premium=2.0,
            call_strike=45.0,
            call_premium=1.5,
            call_covered_quantity=100,
        )


def test_collar_zero_covered_quantity_rejected():
    with pytest.raises(ValueError, match="call_covered_quantity must be positive"):
        collar(
            position_quantity=100,
            current_price=50.0,
            put_strike=45.0,
            put_premium=2.0,
            call_strike=55.0,
            call_premium=1.5,
            call_covered_quantity=0,
        )


def test_collar_oversized_naked_call_is_structurally_rejected():
    """
    THE most important test in this module (HEDGING_SPEC.md Section 6):
    an attempt to sell a call covering MORE than the held position must
    be rejected outright -- not silently clamped to position_quantity,
    not accepted and merely flagged, not partially constructed as a UAP
    and then invalidated downstream. A ValueError, naming the exact
    naked-call risk, before any UAP is ever built.
    """
    with pytest.raises(ValueError) as exc_info:
        collar(
            position_quantity=100,
            current_price=50.0,
            put_strike=45.0,
            put_premium=2.0,
            call_strike=55.0,
            call_premium=1.5,
            call_covered_quantity=150,  # exceeds the held 100 shares
        )
    message = str(exc_info.value)
    assert "150" in message and "100" in message
    assert "naked" in message.lower() or "uncovered" in message.lower()
    assert "Section 6" in message


def test_collar_covered_quantity_exactly_equal_to_position_is_allowed():
    # Exact-boundary case: call_covered_quantity == position_quantity
    # must NOT be rejected -- only strictly exceeding it should be.
    uap = collar(
        position_quantity=100,
        current_price=50.0,
        put_strike=45.0,
        put_premium=2.0,
        call_strike=55.0,
        call_premium=1.5,
        call_covered_quantity=100,
    )
    assert uap.result["uncollared_quantity"] == 0
