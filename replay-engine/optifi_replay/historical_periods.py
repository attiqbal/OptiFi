"""
The historical replay dataset — PHASE E5 brief, Part 4: "Begin with a
manageable set of historically meaningful periods representing multiple
regimes. Do not cherry-pick only successful periods."

Seven periods, matching the brief's own named list exactly. Each reuses
forecast-engine's EXISTING synthetic generators
(`synthetic_cpi_yoy_series`, `synthetic_index_returns`) — unmodified,
no new generator code — with distinct, honestly-documented parameters
per regime and a distinct seed, so periods are genuinely different draws
under genuinely different statistical character, not the same noise
wearing seven labels.

IMPORTANT — same synthetic-data honesty discipline as every prior phase:
these are NOT real historical episodes. This project has no real market/
macro data connected (`DATA_SOURCE_REGISTRY.md`). "Inflation shock" here
means "a synthetic CPI series parameterised to run persistently hot and
volatile," not a reconstruction of any real inflation episode. Treat
regime LABELS as scenario-design metadata, not historical claims.

Calendar: CPI is monthly, index returns are daily — one shared day-count
clock (`month_offset_date(m) := anchor + 30*m days`, a fixed, simplified
30-day month rather than true calendar arithmetic) keeps the two axes
directly comparable, which matters: `as_of` is derived from
`cpi_cutoff_month` alone, and `index_n_days` must genuinely exceed
`cpi_cutoff_month * 30` for the daily series to have any real "future"
portion beyond that same `as_of` for `build_snapshot`'s filtering to
actually exercise (not just the monthly series) — an earlier version of
this module picked the two cutoffs independently, which meant the daily
series never had anything to exclude; fixed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from optifi_forecast import synthetic_cpi_yoy_series, synthetic_index_returns

_ANCHOR_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)
_DAYS_PER_MONTH = 30  # fixed, simplified — not true calendar arithmetic


def month_offset_date(month_index: int) -> datetime:
    """Deterministic synthetic calendar, monthly axis — no real dates."""
    return _ANCHOR_DATE + timedelta(days=_DAYS_PER_MONTH * month_index)


def day_offset_date(day_index: int) -> datetime:
    """Deterministic synthetic calendar, daily axis — shares `month_offset_date`'s anchor and day-count basis."""
    return _ANCHOR_DATE + timedelta(days=day_index)


@dataclass(frozen=True)
class HistoricalPeriod:
    period_id: str
    regime_label: str
    description: str
    # CPI (monthly) series generation parameters
    cpi_seed: int
    cpi_level: float
    cpi_phi: float
    cpi_innovation_std: float
    cpi_n_months: int
    cpi_cutoff_month: int
    # Index-return (daily) series generation parameters — reused here as
    # a stand-in for whichever market-type series a given period's
    # narrative concerns (equity, FX, commodity) — forecast-engine has
    # only one such generator; see the module docstring's honesty note.
    index_seed: int
    index_annual_mean: float
    index_annual_vol: float
    index_n_days: int

    def __post_init__(self) -> None:
        # The whole point of sharing one calendar clock (module
        # docstring): the daily series must extend far enough past the
        # monthly cutoff for there to be genuine "future" daily data for
        # build_snapshot to exclude, not just future monthly data.
        if self.index_n_days <= self.index_cutoff_day:
            raise ValueError(
                f"{self.period_id}: index_n_days ({self.index_n_days}) must exceed "
                f"the derived index cutoff ({self.index_cutoff_day} = "
                f"cpi_cutoff_month * {_DAYS_PER_MONTH}) — otherwise the daily series "
                "has no genuine future portion for the freeze mechanism to exclude."
            )

    @property
    def as_of(self) -> datetime:
        return month_offset_date(self.cpi_cutoff_month)

    @property
    def index_cutoff_day(self) -> int:
        """Derived, not independently chosen — see module docstring."""
        return self.cpi_cutoff_month * _DAYS_PER_MONTH

    def cpi_series(self) -> list[float]:
        return synthetic_cpi_yoy_series(
            seed=self.cpi_seed,
            n_months=self.cpi_n_months,
            level=self.cpi_level,
            phi=self.cpi_phi,
            innovation_std=self.cpi_innovation_std,
        )

    def index_returns(self) -> list[float]:
        return synthetic_index_returns(
            seed=self.index_seed,
            n_days=self.index_n_days,
            annual_mean=self.index_annual_mean,
            annual_vol=self.index_annual_vol,
        )

    def index_price_levels(self) -> list[float]:
        """Cumulative index level (base 100) from `index_returns()` —
        the one real price series `decision_package.py` (market UAPs)
        and `scorecard.py` (realised-outcome extraction) both need;
        computed once here rather than duplicated in both."""
        levels = []
        level = 100.0
        for r in self.index_returns():
            level *= 1 + r
            levels.append(level)
        return levels


# 24 months of history + 6 months of "future" CPI data (cutoff at month
# 24 of a 30-month series); the daily index series must span past
# 24*30=720 days for the same reason — 840 days gives 120 days of
# genuine "future" daily data past the shared as_of, comfortably
# covering a 3-month (~90 trading day) post-as_of evaluation window
# (Part 3's realised-outcome comparison, scorecard.py).
_DEFAULT_CPI_N_MONTHS = 30
_DEFAULT_CPI_CUTOFF = 24
_DEFAULT_INDEX_N_DAYS = 840


CALM_MARKETS = HistoricalPeriod(
    period_id="calm_markets",
    regime_label="calm",
    description="Low, stable inflation; low equity-market volatility.",
    cpi_seed=101, cpi_level=2.0, cpi_phi=0.90, cpi_innovation_std=0.15,
    cpi_n_months=_DEFAULT_CPI_N_MONTHS, cpi_cutoff_month=_DEFAULT_CPI_CUTOFF,
    index_seed=201, index_annual_mean=0.08, index_annual_vol=0.10,
    index_n_days=_DEFAULT_INDEX_N_DAYS,
)

TIGHTENING = HistoricalPeriod(
    period_id="tightening",
    regime_label="tightening-cycle",
    description="Elevated, persistent inflation consistent with a central-bank tightening cycle; muted equity returns.",
    cpi_seed=102, cpi_level=4.0, cpi_phi=0.85, cpi_innovation_std=0.30,
    cpi_n_months=_DEFAULT_CPI_N_MONTHS, cpi_cutoff_month=_DEFAULT_CPI_CUTOFF,
    index_seed=202, index_annual_mean=0.04, index_annual_vol=0.16,
    index_n_days=_DEFAULT_INDEX_N_DAYS,
)

EASING = HistoricalPeriod(
    period_id="easing",
    regime_label="easing-cycle",
    description="Below-target inflation consistent with a central-bank easing cycle; supportive equity returns.",
    cpi_seed=103, cpi_level=1.5, cpi_phi=0.90, cpi_innovation_std=0.20,
    cpi_n_months=_DEFAULT_CPI_N_MONTHS, cpi_cutoff_month=_DEFAULT_CPI_CUTOFF,
    index_seed=203, index_annual_mean=0.10, index_annual_vol=0.14,
    index_n_days=_DEFAULT_INDEX_N_DAYS,
)

INFLATION_SHOCK = HistoricalPeriod(
    period_id="inflation_shock",
    regime_label="high-inflation",
    description="High, volatile, persistent inflation readings; depressed equity returns and elevated volatility.",
    cpi_seed=104, cpi_level=7.0, cpi_phi=0.95, cpi_innovation_std=0.60,
    cpi_n_months=_DEFAULT_CPI_N_MONTHS, cpi_cutoff_month=_DEFAULT_CPI_CUTOFF,
    index_seed=204, index_annual_mean=0.02, index_annual_vol=0.24,
    index_n_days=_DEFAULT_INDEX_N_DAYS,
)

EQUITY_STRESS = HistoricalPeriod(
    period_id="equity_stress",
    regime_label="crisis",
    description="Sharp negative equity returns with elevated volatility (crash-like conditions); moderate inflation.",
    cpi_seed=105, cpi_level=3.0, cpi_phi=0.88, cpi_innovation_std=0.25,
    cpi_n_months=_DEFAULT_CPI_N_MONTHS, cpi_cutoff_month=_DEFAULT_CPI_CUTOFF,
    index_seed=205, index_annual_mean=-0.15, index_annual_vol=0.35,
    index_n_days=_DEFAULT_INDEX_N_DAYS,
)

RECESSION_FEAR = HistoricalPeriod(
    period_id="recession_fear",
    regime_label="recession-fear",
    description="Persistent negative equity drift and falling inflation, consistent with anticipated economic contraction.",
    cpi_seed=106, cpi_level=2.5, cpi_phi=0.93, cpi_innovation_std=0.20,
    cpi_n_months=_DEFAULT_CPI_N_MONTHS, cpi_cutoff_month=_DEFAULT_CPI_CUTOFF,
    index_seed=206, index_annual_mean=-0.08, index_annual_vol=0.28,
    index_n_days=_DEFAULT_INDEX_N_DAYS,
)

FX_COMMODITY_VOLATILITY = HistoricalPeriod(
    period_id="fx_commodity_volatility",
    regime_label="high-volatility",
    description=(
        "Choppy, directionless, high-volatility conditions standing in for volatile FX/commodity "
        "markets — forecast-engine has no dedicated FX/commodity generator yet (see the Phase E4/E5 "
        "deliverables' own honestly-stated gap), so the general fat-tailed index-return generator is "
        "reused here with zero drift and high volatility rather than inventing a new generator."
    ),
    cpi_seed=107, cpi_level=3.0, cpi_phi=0.85, cpi_innovation_std=0.30,
    cpi_n_months=_DEFAULT_CPI_N_MONTHS, cpi_cutoff_month=_DEFAULT_CPI_CUTOFF,
    index_seed=207, index_annual_mean=0.0, index_annual_vol=0.30,
    index_n_days=_DEFAULT_INDEX_N_DAYS,
)

REPLAY_PERIODS: tuple[HistoricalPeriod, ...] = (
    CALM_MARKETS,
    TIGHTENING,
    EASING,
    INFLATION_SHOCK,
    EQUITY_STRESS,
    RECESSION_FEAR,
    FX_COMMODITY_VOLATILITY,
)


def get_period(period_id: str) -> HistoricalPeriod:
    for period in REPLAY_PERIODS:
        if period.period_id == period_id:
            return period
    raise KeyError(
        f"get_period: {period_id!r} is not a known replay period — "
        f"known ids: {[p.period_id for p in REPLAY_PERIODS]!r}."
    )
