"""
Tests for factor_sensitivity.py — PHASE E4 Part 3: statistical vs.
deterministic asset-response sensitivities.
"""

import numpy as np
import pytest
from optifi_shared import ConfidenceLevel, InformationClass, InsufficientDataFailure

from optifi_quant.factor_sensitivity import (
    DEFAULT_MIN_OBSERVATIONS,
    duration_price_sensitivity,
    estimate_factor_sensitivity,
)

# --- estimate_factor_sensitivity (statistical) ---


def _synthetic_factor_and_asset(seed: int = 1, n: int = 40, true_beta: float = 2.0):
    """SYNTHETIC paired series with a KNOWN true beta, for correctness
    verification — asset = true_beta * factor + independent noise."""
    rng = np.random.default_rng(seed)
    factor = rng.normal(0, 0.02, n)
    noise = rng.normal(0, 0.005, n)
    asset = true_beta * factor + noise
    return factor.tolist(), asset.tolist()


def test_recovers_a_known_true_beta_approximately():
    factor, asset = _synthetic_factor_and_asset(true_beta=2.0)
    uap = estimate_factor_sensitivity("factor:yield", "asset:duration-fund", factor, asset, horizon="1-month")
    assert uap.result["sensitivity"] == pytest.approx(2.0, abs=0.3)
    assert uap.result["method"] == "statistical-ols"


def test_sensitivity_matches_independent_numpy_ols_recomputation():
    """Cross-check via a completely separate computation path
    (numpy.polyfit) rather than trusting covariance_matrix's own
    internals a second time."""
    factor, asset = _synthetic_factor_and_asset(seed=7, true_beta=-1.5)
    uap = estimate_factor_sensitivity("factor:fx", "asset:exporter-equities", factor, asset, horizon="1-month")

    independent_beta, _ = np.polyfit(factor, asset, deg=1)
    assert uap.result["sensitivity"] == pytest.approx(independent_beta, rel=1e-9)


def test_r_squared_is_between_zero_and_one_for_a_real_relationship():
    factor, asset = _synthetic_factor_and_asset(true_beta=3.0)
    uap = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")
    assert 0.0 <= uap.result["r_squared"] <= 1.0
    assert uap.result["r_squared"] > 0.5  # strong synthetic relationship should show up clearly


def test_horizon_and_regime_are_recorded_on_the_result():
    factor, asset = _synthetic_factor_and_asset()
    uap = estimate_factor_sensitivity(
        "factor:x", "asset:y", factor, asset, horizon="1-quarter", regime="high-inflation"
    )
    assert uap.result["horizon"] == "1-quarter"
    assert uap.result["regime"] == "high-inflation"


def test_regime_none_by_default():
    factor, asset = _synthetic_factor_and_asset()
    uap = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")
    assert uap.result["regime"] is None


def test_confidence_downgraded_for_small_sample_even_above_the_hard_floor():
    factor, asset = _synthetic_factor_and_asset(n=DEFAULT_MIN_OBSERVATIONS + 1)
    uap = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")
    assert uap.confidence == ConfidenceLevel.LOW


def test_confidence_moderate_for_a_robust_sample():
    factor, asset = _synthetic_factor_and_asset(n=100)
    uap = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")
    assert uap.confidence == ConfidenceLevel.MODERATE


# --- Testing Requirement: "sensitivity estimated from insufficient history" ---


def test_insufficient_history_raises():
    factor, asset = _synthetic_factor_and_asset(n=DEFAULT_MIN_OBSERVATIONS - 1)
    with pytest.raises(InsufficientDataFailure):
        estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")


def test_exactly_at_the_minimum_is_accepted():
    factor, asset = _synthetic_factor_and_asset(n=DEFAULT_MIN_OBSERVATIONS)
    uap = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")
    assert uap.result["n_observations"] == DEFAULT_MIN_OBSERVATIONS


def test_mismatched_series_lengths_raise():
    factor, asset = _synthetic_factor_and_asset(n=20)
    with pytest.raises(ValueError):
        estimate_factor_sensitivity("factor:x", "asset:y", factor, asset[:-1], horizon="1-month")


def test_zero_variance_factor_raises():
    factor = [0.01] * 20
    asset = list(np.random.default_rng(1).normal(0, 0.01, 20))
    with pytest.raises(ValueError):
        estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")


def test_dependencies_reference_the_covariance_matrix_computation():
    factor, asset = _synthetic_factor_and_asset()
    uap = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")
    assert len(uap.dependencies) == 1


def test_disagreement_set_ref_is_passed_through_when_supplied():
    factor, asset = _synthetic_factor_and_asset()
    uap = estimate_factor_sensitivity(
        "factor:x", "asset:y", factor, asset, horizon="1-month", disagreement_set_ref="competing-models-x-y"
    )
    assert uap.disagreement_set_ref == "competing-models-x-y"


# --- duration_price_sensitivity (deterministic) ---


def test_duration_sensitivity_matches_hand_computed_formula():
    uap = duration_price_sensitivity(modified_duration=7.5)
    assert uap.result["sensitivity"] == pytest.approx(-7.5)
    assert uap.result["method"] == "deterministic-duration"


def test_duration_sensitivity_zero_duration_gives_zero_sensitivity():
    uap = duration_price_sensitivity(modified_duration=0.0)
    assert uap.result["sensitivity"] == 0.0


def test_negative_duration_rejected():
    with pytest.raises(ValueError):
        duration_price_sensitivity(modified_duration=-2.0)


def test_duration_sensitivity_is_estimate_and_provisional():
    uap = duration_price_sensitivity(modified_duration=5.0)
    assert uap.information_class == InformationClass.ESTIMATE
    assert uap.confidence == ConfidenceLevel.MODERATE  # never HIGH — see module docstring


def test_deterministic_and_statistical_methods_are_distinguishable():
    """Part 3: 'keep deterministic relationships separate from
    statistical relationships' — proven directly: the `method` field
    never conflates the two."""
    factor, asset = _synthetic_factor_and_asset()
    statistical = estimate_factor_sensitivity("factor:x", "asset:y", factor, asset, horizon="1-month")
    deterministic = duration_price_sensitivity(modified_duration=5.0)
    assert statistical.result["method"] != deterministic.result["method"]
    assert statistical.result["method"] == "statistical-ols"
    assert deterministic.result["method"] == "deterministic-duration"
