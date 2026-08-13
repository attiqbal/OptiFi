# evaluation-engine

Owns Stage 14 (Outcome Tracking & Model Evaluation) —
`ENGINE_PIPELINE_SPECIFICATION.md` Section 9, resolved in Phase E3 (see
that document's Section 12, item 1, for why this became a new top-level
package rather than an extension of `verification-engine` or
`forecast-engine`).

Tracks forecasts (and, in future, recommendations) against realised
outcomes; computes target-appropriate evaluation metrics; maintains
per-model scorecards; and feeds performance history back into
`forecast-engine`'s confidence calibration and performance-weighted
ensembles. Never mathematically resolves disagreement between competing
models on its own initiative — it scores them, `forecast-engine`'s
ensemble functions (or, ultimately, a human) decide what to do with those
scores.

No live model, no live outcome data — see `forecast-engine`'s synthetic
data module (`optifi_forecast/synthetic_data.py`) for the SYNTHETIC series
this package's own tests evaluate against.
