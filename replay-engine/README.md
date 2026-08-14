# replay-engine

Historical replay and decision reconstruction — the cross-cutting
capability documented in `ENGINE_PIPELINE_SPECIFICATION.md` Section 12,
item 7 (Phase E5): "reconstruct exactly what OptiFi could have known and
concluded at a historical point in time," then evaluate that
reconstructed decision against what actually happened.

Not a stage of its own — it orchestrates existing, unmodified functions
from `data-engine`, `causal-engine`, `forecast-engine`,
`evaluation-engine`, `simulation-engine`, `quant-engine`,
`optimisation-engine`, and `verification-engine` under a frozen
information cutoff (`as_of`), then hands the result to
`evaluation-engine` for outcome tracking. Implements no novel analytical
methodology of its own.

No live model, no live historical data — see `historical_periods.py` for
the SYNTHETIC replay dataset (seven regime-labelled periods) this
package's own tests replay against; portfolio/mandate structures are the
same illustrative constants already established elsewhere in this
project (`tests/integration/test_vertical_slice.py`), not a real
per-user Financial Twin, which does not exist as code yet.
