"""
Tests for SensitivityRegistry — PHASE E4 Part 4 (regime conditioning)
and the required "regime mismatch" / "conflicting asset-response models"
adversarial tests.
"""

import pytest
from optifi_shared import ConflictedInputFailure, MissingInputFailure, OutOfDistributionFailure

from optifi_quant import duration_price_sensitivity, estimate_factor_sensitivity, SensitivityRegistry


def _sensitivity(value: float, regime: str | None = None):
    """A minimal, valid sensitivity UAP for registry tests — reuses the
    real deterministic function so every entry is a genuine UAP, not a
    hand-built stand-in, then overrides regime/sensitivity directly on
    its `result` dict where the test needs a specific combination."""
    uap = duration_price_sensitivity(modified_duration=abs(value))
    return uap.model_copy(update={"result": {**uap.result, "sensitivity": value, "regime": regime}})


def test_exact_regime_match_is_returned_without_fallback():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime="high-inflation"))

    result = registry.get_sensitivity("factor:yield", "asset:bonds", regime="high-inflation")
    assert result.regime_matched is True
    assert result.fallback_used is False
    assert len(result.matches) == 1


def test_regime_agnostic_lookup_returns_regime_agnostic_entry():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime=None))

    result = registry.get_sensitivity("factor:yield", "asset:bonds", regime=None)
    assert result.regime_matched is True
    assert result.fallback_used is False


# --- Testing Requirement: "regime mismatch" ---


def test_falls_back_to_regime_agnostic_when_specific_regime_missing():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime=None))

    result = registry.get_sensitivity("factor:yield", "asset:bonds", regime="crisis")
    assert result.regime_matched is False
    assert result.fallback_used is True
    assert result.matches[0].result["sensitivity"] == -5.0


def test_regime_mismatch_with_fallback_disallowed_raises():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime=None))

    with pytest.raises(OutOfDistributionFailure):
        registry.get_sensitivity("factor:yield", "asset:bonds", regime="crisis", allow_fallback=False)


def test_regime_mismatch_with_no_fallback_available_at_all_raises():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime="low-inflation"))

    with pytest.raises(OutOfDistributionFailure):
        registry.get_sensitivity("factor:yield", "asset:bonds", regime="crisis")


# --- Testing Requirement: "missing factor exposure" ---


def test_completely_unregistered_pair_raises_missing_input_not_out_of_distribution():
    """Distinct failure mode from regime mismatch: nothing has EVER been
    estimated for this pair, under any regime — a structural gap, not a
    conditioning problem."""
    registry = SensitivityRegistry()
    with pytest.raises(MissingInputFailure):
        registry.get_sensitivity("factor:nonexistent", "asset:nonexistent")


def test_regime_agnostic_request_does_not_fall_back_to_regime_specific_entry():
    """Fallback only ever goes specific -> general, never the reverse —
    a caller asking for the general estimate must not silently receive
    a regime-specific one, which would understate its conditionality."""
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime="crisis"))

    with pytest.raises(OutOfDistributionFailure):
        registry.get_sensitivity("factor:yield", "asset:bonds", regime=None)


# --- Testing Requirement: "conflicting asset-response models" ---


def test_multiple_competing_estimates_for_the_same_key_are_all_preserved():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime="high-inflation"))
    registry.register("factor:yield", "asset:bonds", _sensitivity(-8.0, regime="high-inflation"))

    result = registry.get_sensitivity("factor:yield", "asset:bonds", regime="high-inflation")
    assert len(result.matches) == 2
    values = {m.result["sensitivity"] for m in result.matches}
    assert values == {-5.0, -8.0}


def test_single_raises_when_multiple_competing_estimates_exist():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime="high-inflation"))
    registry.register("factor:yield", "asset:bonds", _sensitivity(-8.0, regime="high-inflation"))

    result = registry.get_sensitivity("factor:yield", "asset:bonds", regime="high-inflation")
    with pytest.raises(ConflictedInputFailure):
        result.single()


def test_single_succeeds_when_exactly_one_match():
    registry = SensitivityRegistry()
    registry.register("factor:yield", "asset:bonds", _sensitivity(-5.0, regime="high-inflation"))

    result = registry.get_sensitivity("factor:yield", "asset:bonds", regime="high-inflation")
    assert result.single().result["sensitivity"] == -5.0


def test_registry_works_with_real_statistical_sensitivity_uaps_too():
    import numpy as np

    rng = np.random.default_rng(0)
    factor = rng.normal(0, 0.02, 40).tolist()
    asset = (2.0 * np.array(factor) + rng.normal(0, 0.005, 40)).tolist()
    real_uap = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")

    registry = SensitivityRegistry()
    registry.register("factor:x", "asset:y", real_uap)
    result = registry.get_sensitivity("factor:x", "asset:y", regime=None)
    assert result.single().id == real_uap.id
