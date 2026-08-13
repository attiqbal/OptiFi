# forecast-engine

Stage 6 of the pipeline: forecasting (`FORECAST_ENGINE_SPEC.md`).

**Implemented:**
- Three selected forecasting targets (macro inflation, market
  volatility, company revenue-growth direction), each with a documented
  justification
- Simple baselines (naive, historical mean, rolling mean, AR(1)) and two
  competing model families (statistical exponential smoothing, a
  feature-based ML linear model)
- A walk-forward temporal-validation harness with strict train/test
  time separation (`temporal.py`)
- Confidence calibration and performance-weighted ensembling, both wired
  to `evaluation-engine`'s model scorecards
- Frozen/immutable historical predictions with model-version-change
  handling
- 79 automated tests

**Not yet implemented:**
- Any real historical time series — every current example runs on
  clearly-labelled synthetic data (`synthetic_data.py`); no real vendor
  is connected (see `data-engine`)
- Production model selection within each family — this package
  demonstrates the evaluation methodology, not a chosen production model
