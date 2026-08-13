# FORECAST_ENGINE_SPEC

**Status:** DRAFT (v1.2 — Phase E3, patch: Section 9 item 4 resolved)

## 1. Purpose & Scope

This document specifies `forecast-engine`'s Stage 6 output, its model
families, and — resolving a question open since Phase 1B — the
ensemble/aggregation mechanism for combining disagreeing forecasts. It does
not choose specific model implementations.

## 2. Relationship to Prior Documents

Elaborates `ENGINE_PIPELINE_SPECIFICATION.md` Stage 6.
`ENGINE_PIPELINE_SPECIFICATION.md` Section 7 uses forecast disagreement
(an econometric forecast, an ML forecast, and a market-implied forecast
disagreeing on recession probability) as its canonical illustration of
the multi-model disagreement principle — no specific percentages are
fixed in that source. `ANALYTICAL_CONTRACT_SPEC.md` Section 7 states the
same principle in contract terms but left the actual ensemble mechanism
undesigned — resolved in Section 6 below.
Confirms (or not) the `SECURITY.md` Section 11, item 2 assumption — see
Section 3.

## 3. Confirming the `SECURITY.md` Assumption

Consistent with `CAUSAL_ENGINE_SPEC.md`'s confirmation for `causal-engine`:
`forecast-engine` operates on shared macro/market data to produce general
forecasts (e.g. "UK recession probability, 12-month horizon") rather than
per-user forecasts. It does not need raw per-user Financial Twin access —
applying a forecast to a specific user's portfolio happens downstream, in
`quant-engine` or `simulation-engine`. A follow-up patch to `SECURITY.md`
completing Section 11, item 2 for `forecast-engine` (alongside
`simulation-engine`, still pending) is needed and not performed here.

## 4. Forecasting Targets & Horizons

Targets include macro variables (rates, inflation, GDP, employment) and
market variables (sector returns, volatility) — not an exhaustive list, a
category description. Horizons are explicitly bounded (e.g. 3-month,
12-month) — an unbounded forecast is not a valid output; every forecast
states the horizon it applies to.

## 5. Model Families

Three broad families, consistent with the canonical example already
established in `ANALYTICAL_CONTRACT_SPEC.md`:

- **Econometric time-series models** — statistical models fit to historical
  data.
- **Machine-learning models** — pattern-based models trained on broader
  feature sets.
- **Market-implied models** — probabilities or expectations derived from
  current market pricing (e.g. options, yield curves) rather than fit to
  history.

Which specific model within each family is used for a given target is not
decided here — that is real data-science work requiring backtesting.

## 6. The Ensemble/Aggregation Mechanism — Resolved

When multiple model families produce forecasts for the same `subject`,
`forecast-engine` **may** additionally compute an explicit ensemble
estimate. This is always an *additional* UAP alongside the individual model
outputs, linked via `disagreement_set_ref` — **never a replacement.** The
individual forecasts remain visible to `ai-engine` regardless of whether an
ensemble was computed, consistent with `ANALYTICAL_CONTRACT_SPEC.md`
Section 7's requirement that the CIO explain disagreement rather than have
it hidden before Stage 12.

Two standard weighting approaches:

- **Simple average:** `forecast_ensemble = (1/n) Σ f_i`
- **Inverse-error weighting** (weights models by historical accuracy):
  `w_i = (1/error_i) / Σ(1/error_j)`, then
  `forecast_ensemble = Σ(w_i × f_i)`, where `error_i` is model `i`'s
  historical forecast error (Section 7).

Which weighting scheme applies by default, or whether Bayesian model
averaging is used instead, is not fixed here — see Section 9.

The ensemble's own `confidence` should reflect agreement among its inputs —
low agreement between constituent models should widen the ensemble's
uncertainty bounds, not narrow them through averaging alone.

## 7. Forecast Evaluation

Every forecast is eventually checked against realised outcomes:

- **Point forecasts:** evaluated via standard error metrics (e.g. RMSE,
  MAE) against what actually occurred.
- **Probabilistic forecasts:** evaluated via calibration — a stated 70%
  confidence interval should contain the true outcome approximately 70% of
  the time across many forecasts, not just look reasonable on any single
  one.

This evaluation methodology is a natural candidate input to **Stage 14
(Outcome Tracking & Model Evaluation)**, whose engine ownership was
unresolved since Phase 1A (`ENGINE_PIPELINE_SPECIFICATION.md` Section 12).
**RESOLVED in Phase E3:** a new `evaluation-engine` package now owns Stage
14 — see that document's Section 12 item 1 for the alternatives considered
(extending `verification-engine`; extending `forecast-engine` itself;
treating it as an `infrastructure` concern) and why each was rejected.
`evaluation-engine` implements this section's point/probabilistic
evaluation methodology directly, using `forecast-engine`'s own forecast
UAPs (point forecast, uncertainty bounds, model identity) as its input —
`forecast-engine` produces forecasts and remains the source of the model
identity/version Stage 14 scores; it does not itself compute or store
evaluation results.

## 8. Uncertainty Is Mandatory

Consistent with Stage 6's existing rule, a forecast is never a bare point
estimate — it carries explicit uncertainty (a range or a distribution
across outcomes), matching the style already established in
`PRODUCT_VISION.md`'s forecasting philosophy (e.g. a probability
distribution across "25bp cut," "no change," "increase," rather than a
single predicted value).

## 9. Known Gaps / Open Questions

1. Which weighting scheme (simple average, inverse-error weighting,
   Bayesian model averaging, or another) applies by default is not fixed —
   left as available options.
2. Specific model implementations within each family (Section 5) are not
   chosen — genuine implementation-level, data-driven decisions.
3. ~~A follow-up patch to `SECURITY.md` confirming `forecast-engine`
   doesn't need raw per-user Twin access...~~ **RESOLVED:** that patch
   was completed — `SECURITY.md` Section 11, item 2 now cites this
   document's Section 3 as part of its full confirmation.
4. ~~Stage 14's ownership remains unresolved...~~ **RESOLVED (Phase E3):**
   see Section 7 above and `ENGINE_PIPELINE_SPECIFICATION.md` Section 12
   item 1 — `evaluation-engine` now owns Stage 14.
