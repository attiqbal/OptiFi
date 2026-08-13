"""
The three forecasting targets — PHASE E3 brief, Part A.

"Do NOT select targets simply because they are easy. Choose targets that
could genuinely matter to downstream portfolio decisions. Document why
each target is useful." One target per FORECAST_ENGINE_SPEC.md Section 4
category (macro / market / sector-company), and — deliberately — one
target per Evaluation Metrics shape (Part E) not otherwise exercised, so
this phase's evaluation engine demonstrates all four metric families
against genuine (if synthetic) forecasting problems rather than one
narrow shape repeated three times:

1. **Macro** — UK CPI YoY inflation, 3-month horizon. POINT + PROBABILITY.
2. **Market** — synthetic broad-market realised volatility, 1-month
   horizon. POINT + INTERVAL.
3. **Sector/Company** — SYNTH_ACME next-quarter revenue-growth direction.
   DIRECTION.

Each target below states its own `data_note` — whether it is genuinely
tied to `data-engine`'s existing fixture identifiers (Phase E2) or is
purely a forecasting-methodology exercise on extended synthetic data
(`synthetic_data.py`) because no real historical time series is
connected. This project has not connected a real vendor
(`DATA_SOURCE_REGISTRY.md` Section 7) — the "no real data" limitation is
stated explicitly here and in the Phase E3 deliverable's Limitations
section, not silently glossed over.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastTarget:
    target_id: str
    subject: str
    horizon: str
    justification: str
    data_note: str


MACRO_CPI_TARGET = ForecastTarget(
    target_id="macro_cpi_yoy_3m",
    subject="UK CPI YoY, 3-month horizon",
    horizon="3-month",
    justification=(
        "Inflation path drives real-return expectations, expected policy-rate "
        "direction, and fixed-income vs. equity allocation tilts — directly "
        "relevant to portfolio decisions (QUANT_ENGINE_SPEC.md's risk-metrics "
        "consumers, OPTIMISATION_ENGINE_SPEC.md's constraint set). CPI YoY is "
        "also the specific indicator DATA_SOURCE_REGISTRY.md Section 7.2 and "
        "data-engine's Phase E2 fixture (SYNTH_CPI) already model, so the "
        "revision/vintage handling this phase's evaluation engine must "
        "exercise (Part I / 'revised macro data') has a genuine, already-built "
        "counterpart to hook into (data-engine's ingest_macro_observation)."
    ),
    data_note=(
        "SYNTH_CPI (Phase E2 fixture) demonstrates real ingestion/revision "
        "mechanics but is a single snapshot, not a time series — genuine "
        "walk-forward backtesting needs many periods. synthetic_data.py's "
        "synthetic_cpi_yoy_series() extends this with a ~60-month SYNTHETIC "
        "mean-reverting series for backtesting only; SYNTH_CPI itself remains "
        "the real (if singular) ingested fixture used for the vintage-"
        "consistency demonstration."
    ),
)

MARKET_VOLATILITY_TARGET = ForecastTarget(
    target_id="market_realised_vol_1m",
    subject="synthetic broad-market index, realised volatility, 1-month horizon",
    horizon="1-month",
    justification=(
        "Volatility forecasts feed directly into quant-engine's risk analytics "
        "(parametric/historical VaR, Section 5.3) and optimisation-engine's "
        "constraint set (risk tolerance) — a forward-looking volatility view "
        "materially changes recommended position sizing, not just a "
        "backward-looking risk figure. This is also the target Part B's "
        "'market-implied expectation where available' baseline would most "
        "naturally apply to (an options-implied vol index) — its absence "
        "here is a genuine, documented data gap, not an oversight (see "
        "Limitations)."
    ),
    data_note=(
        "No real index price history is connected (DATA_SOURCE_REGISTRY.md "
        "Section 7.1 — Category A adapters are all NOT CONNECTED). "
        "synthetic_data.py's synthetic_index_returns() extends quant-engine's "
        "own established SYNTHETIC daily-returns generator "
        "(tests/conftest.py's synthetic_realistic_daily_returns — fat-tailed, "
        "fixed-seed) to ~500 trading days purely for this phase's "
        "walk-forward demonstration."
    ),
)

COMPANY_REVENUE_DIRECTION_TARGET = ForecastTarget(
    target_id="company_revenue_growth_direction_1q",
    subject="SYNTH_ACME quarterly revenue growth, direction (up/down vs. prior quarter)",
    horizon="1-quarter",
    justification=(
        "Earnings-revision/growth-direction calls are a canonical "
        "stock-specific input to sector tilts and single-name conviction "
        "sizing — the brief's own named example. Framed as a DIRECTION "
        "target specifically (rather than a further point forecast) so "
        "this phase's evaluation engine exercises accuracy/precision/recall "
        "and the economic-value proxy (Part E), the one metric family the "
        "other two targets do not naturally exercise."
    ),
    data_note=(
        "SYNTH_ACME (Phase E2 fixture) is a single market-price observation, "
        "not a revenue series — this target needs company FUNDAMENTALS "
        "(Category C), which Phase E2 defined but did not build an example "
        "fixture for. synthetic_data.py's synthetic_company_revenue_growth() "
        "generates a ~20-quarter SYNTHETIC revenue-growth series against the "
        "same SYNTH_ACME identifier for continuity with the existing fixture "
        "naming, clearly labelled synthetic throughout."
    ),
)

ALL_TARGETS: tuple[ForecastTarget, ...] = (
    MACRO_CPI_TARGET,
    MARKET_VOLATILITY_TARGET,
    COMPANY_REVENUE_DIRECTION_TARGET,
)
