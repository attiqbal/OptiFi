"""
Extended SYNTHETIC time series for genuine walk-forward backtesting —
PHASE E3's "data scarcity" fork (see the deliverable's Limitations
section): this project has not connected a real market/macro data vendor
(`DATA_SOURCE_REGISTRY.md` Section 7 — every Category A/B/C adapter is
`NOT CONNECTED`), so no real historical series exists to forecast on.

Rather than either (a) fabricate results by presenting synthetic output
as if it were real, or (b) block this entire phase on data that does not
exist yet, this module follows the SAME precedent this project already
established for exactly this situation: `quant-engine/tests/conftest.py`'s
`synthetic_realistic_daily_returns` (fixed-seed, statistically realistic,
loudly and repeatedly labelled SYNTHETIC — never presented as real
history) and `data-engine/optifi_data/fixtures/` (SYNTH_-prefixed
identifiers, its own README warning). Every series below is generated
with a FIXED seed for reproducibility and is NOT real market or economic
history — nothing in this module, or in anything downstream of it,
should be read or presented as an actual historical observation for any
real instrument, index, or economic indicator.

Unlike `quant-engine`'s fixture (which lives in that package's *tests*,
not its installed code, deliberately), these generators are installed
`optifi_forecast` code — Part D's walk-forward harness and the Part B/C
baselines/models need a genuinely long series to operate on, not a
test-only fixture reused by copy-paste (the pattern
`tests/integration/test_vertical_slice.py` had to fall back to for
exactly that reason — see that file's own comment on it).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import t as student_t

# --- Fixed calibration parameters (documented, not arbitrary — same
# --- discipline as quant-engine's conftest.py) ---

SYNTHETIC_SEED = 42

# CPI YoY: a mean-reverting (AR(1)) process around an illustrative 2.5%
# long-run level, with Gaussian innovations. `phi` close to 1 gives
# realistic month-to-month persistence (inflation does not jump
# randomly); `phi < 1` ensures the series is stationary and actually
# mean-reverts rather than random-walking away indefinitely.
CPI_N_MONTHS = 60
CPI_LEVEL = 2.5
CPI_PHI = 0.92
CPI_INNOVATION_STD = 0.35

# Market index: same fat-tailed Student's t construction as
# quant-engine's conftest.py, extended to 3 years of daily data so
# monthly-aggregated realised volatility yields enough points for
# genuine walk-forward validation.
INDEX_N_DAYS = 756  # ~3 trading years
INDEX_DF = 4
INDEX_ANNUAL_MEAN = 0.08
INDEX_ANNUAL_VOL = 0.18
REALISED_VOL_WINDOW_DAYS = 21  # ~1 trading month

# Company revenue growth: AR(1) around an illustrative 3% QoQ growth
# level — noisier and less persistent than macro data (company-specific
# shocks are large relative to the underlying trend).
REVENUE_N_QUARTERS = 20
REVENUE_LEVEL = 0.03
REVENUE_PHI = 0.4
REVENUE_INNOVATION_STD = 0.045


def synthetic_cpi_yoy_series(
    seed: int = SYNTHETIC_SEED,
    n_months: int = CPI_N_MONTHS,
    level: float = CPI_LEVEL,
    phi: float = CPI_PHI,
    innovation_std: float = CPI_INNOVATION_STD,
) -> list[float]:
    """SYNTHETIC monthly UK CPI YoY (%) series — mean-reverting AR(1),
    NOT real ONS data. See module docstring."""
    rng = np.random.default_rng(seed)
    series = [level]
    for _ in range(n_months - 1):
        innovation = rng.normal(0.0, innovation_std)
        next_value = level + phi * (series[-1] - level) + innovation
        series.append(next_value)
    return series


def synthetic_index_returns(
    seed: int = SYNTHETIC_SEED,
    n_days: int = INDEX_N_DAYS,
    df: int = INDEX_DF,
    annual_mean: float = INDEX_ANNUAL_MEAN,
    annual_vol: float = INDEX_ANNUAL_VOL,
) -> list[float]:
    """SYNTHETIC daily returns for an illustrative broad-market index —
    identical construction to quant-engine's own
    synthetic_realistic_daily_returns (fat-tailed Student's t, fixed
    seed), extended in length. NOT real market history."""
    daily_mean = annual_mean / 252
    daily_vol = annual_vol / (252**0.5)
    t_variance = df / (df - 2)
    scale = daily_vol / (t_variance**0.5)
    rng = np.random.default_rng(seed)
    raw_t_draws = student_t.rvs(df=df, size=n_days, random_state=rng)
    return (daily_mean + scale * raw_t_draws).tolist()


def realised_volatility_series(
    daily_returns: list[float], window_days: int = REALISED_VOL_WINDOW_DAYS
) -> list[float]:
    """Non-overlapping `window_days`-day realised volatility (annualised
    stdev of daily returns), one figure per window — the actual monthly
    target series the market-volatility target forecasts. Trailing
    partial windows are dropped (a partial window is not a genuine
    'month' of realised vol)."""
    n_windows = len(daily_returns) // window_days
    result = []
    for i in range(n_windows):
        window = daily_returns[i * window_days : (i + 1) * window_days]
        annualised_vol = float(np.std(window, ddof=1) * (252**0.5))
        result.append(annualised_vol)
    return result


def synthetic_company_revenue_growth(
    seed: int = SYNTHETIC_SEED,
    n_quarters: int = REVENUE_N_QUARTERS,
    level: float = REVENUE_LEVEL,
    phi: float = REVENUE_PHI,
    innovation_std: float = REVENUE_INNOVATION_STD,
) -> list[float]:
    """SYNTHETIC quarterly revenue-growth-rate series for the SYNTH_ACME
    identifier (Phase E2's own fixture naming, for continuity — this is
    NOT the same data as that fixture's single market-price observation).
    AR(1), NOT real company fundamentals."""
    rng = np.random.default_rng(seed + 1)  # distinct stream from CPI's
    series = [level]
    for _ in range(n_quarters - 1):
        innovation = rng.normal(0.0, innovation_std)
        next_value = level + phi * (series[-1] - level) + innovation
        series.append(next_value)
    return series


def revenue_growth_direction_labels(revenue_growth_series: list[float]) -> list[str]:
    """"up" if growth accelerated vs. the prior quarter, "down"
    otherwise — one label per series entry from index 1 onward (index 0
    has no prior quarter to compare against)."""
    return [
        "up" if revenue_growth_series[i] > revenue_growth_series[i - 1] else "down"
        for i in range(1, len(revenue_growth_series))
    ]
