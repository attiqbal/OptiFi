"""
Shared pytest fixtures for quant-engine tests.

`synthetic_realistic_daily_returns` is SYNTHETIC data with realistic
statistical properties (fat-tailed, equity-like mean/volatility),
generated with a fixed random seed for reproducibility. It is NOT real
market history. This project has no connected real market data source —
DATA_SOURCE_REGISTRY.md never named one — and real market data integration
remains a separate, deferred decision. Nothing in this fixture, or in any
test that consumes it, should be read as, or presented as, an actual
historical price or return series for any real instrument or index.
"""

import statistics

import numpy as np
import pytest
from scipy.stats import t as student_t

# --- Fixed calibration parameters (documented, not arbitrary) ---
#
# SYNTHETIC_SEED: fixed so the generated series is byte-identical on every
# run. Reproducibility is the point here, not variety.
#
# SYNTHETIC_N_DAYS: 252 — the conventional number of trading days in a
# year, used purely to get a "realistic scale" (one year of daily data),
# not because it's tied to any real calendar.
#
# SYNTHETIC_DF: Student's t degrees of freedom. A low value (4) gives
# meaningfully fatter tails than a Gaussian — variance of a standard
# t-distribution is df/(df-2), which is undefined/infinite at df<=2 and
# large but finite at df=4 (=2x a Gaussian's relative tail weight at that
# df). This is a commonly cited order-of-magnitude range in the
# quantitative-finance literature for modelling fat-tailed daily equity
# returns (values roughly in the 3-6 range are typical); 4 was chosen as a
# representative point in that range, not a fitted or sourced value.
#
# SYNTHETIC_ANNUAL_MEAN / SYNTHETIC_ANNUAL_VOL: 8% annual mean return and
# 18% annual volatility — round, illustrative, equity-index-scale figures
# (broadly in the range often associated with a diversified equity index
# over long periods), not derived from any specific real index or dataset.
SYNTHETIC_SEED = 42
SYNTHETIC_N_DAYS = 252
SYNTHETIC_DF = 4
SYNTHETIC_ANNUAL_MEAN = 0.08
SYNTHETIC_ANNUAL_VOL = 0.18


def synthetic_realistic_daily_returns(
    seed: int = SYNTHETIC_SEED,
    n_days: int = SYNTHETIC_N_DAYS,
    df: int = SYNTHETIC_DF,
    annual_mean: float = SYNTHETIC_ANNUAL_MEAN,
    annual_vol: float = SYNTHETIC_ANNUAL_VOL,
) -> list[float]:
    """
    Generate a reproducible SYNTHETIC daily-returns series with realistic
    statistical properties — NOT real market history.

    Uses a Student's t-distribution (fatter tails than Gaussian, per `df`)
    scaled and shifted to approximately match `annual_mean`/`annual_vol`
    once annualised. A fixed `seed` makes the output identical on every
    call, which matters more here than variety — this fixture exists to
    give `historical_var` a realistic-scale, fat-tailed input, not to
    simulate any particular real market.
    """
    daily_mean = annual_mean / n_days
    daily_vol = annual_vol / (n_days**0.5)

    # Standard Student's t has variance df/(df-2) for df > 2; scale raw
    # draws so the resulting series' volatility matches `daily_vol`.
    t_variance = df / (df - 2)
    scale = daily_vol / (t_variance**0.5)

    rng = np.random.default_rng(seed)
    raw_t_draws = student_t.rvs(df=df, size=n_days, random_state=rng)
    return (daily_mean + scale * raw_t_draws).tolist()


@pytest.fixture
def synthetic_daily_returns() -> list[float]:
    """
    Pytest fixture wrapping `synthetic_realistic_daily_returns` with the
    module's fixed default parameters. SYNTHETIC data — see the module
    docstring above. Reusable by any future test needing a realistic-scale
    returns series (other metrics, other engines), without regenerating it
    ad hoc.
    """
    return synthetic_realistic_daily_returns()
