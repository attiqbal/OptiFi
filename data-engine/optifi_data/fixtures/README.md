# Fixture Data — SYNTHETIC, NOT REAL MARKET OR ECONOMIC DATA

Every file under this directory is **illustrative, synthetically
generated test data**, used only to prove the ingestion pipeline
(`FixtureProvider` → validation → canonical observation → UAP) works
deterministically, end to end, without a live network dependency or a
real vendor relationship.

**Nothing under this directory is, or should be read as, an actual
historical price, economic release, or corporate event for any real
instrument, index, or company.** Instrument identifiers are deliberately
prefixed `SYNTH_` and indicator/event names are deliberately generic for
exactly this reason — to make confusion with a real data feed
structurally difficult, not just discouraged in prose.

This mirrors the same discipline `quant-engine`'s
`synthetic_realistic_daily_returns` test fixture already established in
this codebase for the same reason.
