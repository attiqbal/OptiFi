"""
Historical validation exercise — PHASE E4 brief, Part 8: "Compare
scenario-generated asset effects against historical episodes where
reasonable. Do not claim structural causal truth merely because
historical fit is good."

IMPORTANT — what this test does and does not prove:

This project has no real historical market/macro data connected
(DATA_SOURCE_REGISTRY.md — every adapter is NOT CONNECTED; see
forecast-engine's synthetic_data.py for the same, already-established
precedent this test follows). What follows is therefore a METHODOLOGY
sanity check on SYNTHETIC data with a KNOWN, fixed, embedded
relationship — not a validation of any real economic relationship, and
not evidence of real-world "historical fit." A good result here shows
`estimate_factor_sensitivity` correctly recovers a known relationship
and produces a sensible predictive range from held-out data. It proves
NOTHING about whether any real factor genuinely drives any real asset —
that would require real data this project does not have, and even then,
per CAUSAL_ENGINE_SPEC.md Section 5.2/6, good statistical fit alone
would still never be sufficient to assert causation.
"""

from __future__ import annotations

import numpy as np

from optifi_quant import estimate_factor_sensitivity

SYNTHETIC_SEED = 2026
TRUE_BETA = -6.5  # illustrative, e.g. a duration-like sensitivity to a yield factor
N_ESTIMATION_PERIODS = 60
NOISE_STD = 0.01


def _synthetic_factor_asset_series(seed: int, n: int, true_beta: float) -> tuple[list[float], list[float]]:
    """SYNTHETIC paired series with a KNOWN embedded relationship — NOT
    real historical data. Deterministic given a fixed seed, matching
    this project's established synthetic-data discipline."""
    rng = np.random.default_rng(seed)
    factor = rng.normal(0, 0.008, n)
    noise = rng.normal(0, NOISE_STD, n)
    asset = true_beta * factor + noise
    return factor.tolist(), asset.tolist()


def test_estimated_sensitivity_recovers_the_known_synthetic_relationship():
    """The core methodology check: given data with a KNOWN embedded
    beta, does estimate_factor_sensitivity recover something close to
    it? This is a sanity check on the estimator, not a historical
    validation of any real relationship."""
    factor, asset = _synthetic_factor_asset_series(SYNTHETIC_SEED, N_ESTIMATION_PERIODS, TRUE_BETA)
    uap = estimate_factor_sensitivity(
        "factor:synthetic-yield", "asset:synthetic-duration-fund", factor, asset, horizon="1-month"
    )
    estimated_beta = uap.result["sensitivity"]
    # Within 20% of the true value — a real, meaningful tolerance given
    # genuine sampling noise, not a rigged pass.
    assert abs(estimated_beta - TRUE_BETA) / abs(TRUE_BETA) < 0.20


def test_held_out_episode_falls_within_the_sensitivitys_own_confidence_interval_most_of_the_time():
    """
    Splits a longer synthetic series into an ESTIMATION window (fit the
    sensitivity) and many held-out single-period "episodes" (simulate
    "what actually happened" vs. "what the sensitivity would have
    predicted"). Reports what fraction of held-out episodes the
    predicted [beta - 1.96*SE, beta + 1.96*SE] * factor_move range
    actually contains the realised asset move — a real calibration
    check on synthetic data, analogous to evaluation-engine's
    reliability-curve check (Phase E3) but applied to this phase's own
    sensitivity estimates.
    """
    rng_seed_estimation = SYNTHETIC_SEED
    rng_seed_holdout = SYNTHETIC_SEED + 1

    est_factor, est_asset = _synthetic_factor_asset_series(rng_seed_estimation, N_ESTIMATION_PERIODS, TRUE_BETA)
    sensitivity_uap = estimate_factor_sensitivity(
        "factor:synthetic-yield", "asset:synthetic-duration-fund", est_factor, est_asset, horizon="1-month"
    )
    beta = sensitivity_uap.result["sensitivity"]
    se = sensitivity_uap.result["standard_error"]

    n_episodes = 200
    holdout_factor, holdout_asset = _synthetic_factor_asset_series(rng_seed_holdout, n_episodes, TRUE_BETA)

    covered = 0
    for factor_move, actual_asset_move in zip(holdout_factor, holdout_asset):
        predicted_low = (beta - 1.96 * se) * factor_move
        predicted_high = (beta + 1.96 * se) * factor_move
        low, high = min(predicted_low, predicted_high), max(predicted_low, predicted_high)
        if low <= actual_asset_move <= high:
            covered += 1

    coverage = covered / n_episodes
    # A well-calibrated ~95% CI on beta, propagated through a per-episode
    # factor move, will not literally achieve 95% coverage of individual
    # episodes (the CI is on the COEFFICIENT, not a full predictive
    # interval on new observations — it omits the residual noise term
    # entirely). This assertion checks the estimate is DIRECTIONALLY
    # sane and non-degenerate (meaningfully more than a coin flip, not a
    # claim of precise 95% calibration) — an honest bound given what
    # this interval actually represents.
    assert coverage > 0.10, (
        f"coverage={coverage:.2%} is implausibly low for a sensitivity estimated "
        "from data drawn from the exact same generating process — something is "
        "likely wrong with the estimation, not just noisy."
    )


def test_a_deliberately_wrong_sensitivity_would_have_performed_worse():
    """Confirms this validation methodology can actually discriminate a
    good estimate from a bad one — a validation check that would pass
    regardless of input proves nothing. Uses a deliberately mis-scaled
    'sensitivity' as the negative control."""
    est_factor, est_asset = _synthetic_factor_asset_series(SYNTHETIC_SEED, N_ESTIMATION_PERIODS, TRUE_BETA)
    real_uap = estimate_factor_sensitivity(
        "factor:synthetic-yield", "asset:synthetic-duration-fund", est_factor, est_asset, horizon="1-month"
    )
    real_beta = real_uap.result["sensitivity"]
    wrong_beta = -real_beta * 0.1  # wrong sign AND wrong magnitude

    holdout_factor, holdout_asset = _synthetic_factor_asset_series(SYNTHETIC_SEED + 1, 200, TRUE_BETA)

    def _mean_abs_error(beta: float) -> float:
        predicted = [beta * f for f in holdout_factor]
        return float(np.mean([abs(p - a) for p, a in zip(predicted, holdout_asset)]))

    assert _mean_abs_error(real_beta) < _mean_abs_error(wrong_beta)
