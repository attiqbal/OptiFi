OptiFi

AI-Powered Financial Intelligence & Capital Optimisation

OptiFi is a research and engineering project building the analytical core of an AI-driven financial intelligence system. It is designed to answer a simple question:

Given what is happening in markets, the economy, and a user's financial position, what should their capital do next?

Instead of relying on one AI model to do everything, OptiFi combines specialist quantitative, forecasting, evaluation, simulation, optimisation, causal, and verification engines, coordinated by an AI layer. Each engine is a real, independently-tested Python package — not a design placeholder — communicating through a shared, auditable data contract described below.

The aim is to build something closer to a personal AI Chief Investment Officer backed by a virtual research team. OptiFi is not a live product: there is no connected market-data vendor, no deployed application, and no real user accounts yet — see "What's Implemented Today" for an honest breakdown of what currently exists.

⸻

Why OptiFi?

Most financial tools are fragmented.

Market data, macroeconomic indicators, portfolio analytics, forecasts, risk models, and financial news often sit in separate systems.

OptiFi brings them together to answer:

* What changed?
* Why does it matter?
* How does it affect this portfolio?
* What could happen next?
* What actions are available?
* Which decisions remain sensible across different scenarios?

The focus is not simply financial information.

It is decision intelligence.

⸻

How OptiFi Works

Data
  ↓
Causal Analysis
  ↓
Forecasting + Quant Analytics
  ↓
Scenario Simulation
  ↓
Optimisation
  ↓
AI CIO
  ↓
Verification
  ↓
User

Forecast evaluation runs alongside this pipeline rather than inside it: every forecast is frozen at the moment it's made, later checked against what actually happened, and that track record feeds back into how much each model is trusted going forward.

OptiFi uses specialist engines for different tasks:

Engine	Role
Data	Ingestion, validation, provenance, deterministic replay
Causal	Economic and financial relationships
Forecast	Baselines, econometric and ML forecasting, ensembling
Evaluation	Tracks forecasts against outcomes; metrics and model scorecards
Quant	Portfolio analytics and risk
Simulation	Scenario generation and Monte Carlo analysis
Optimisation	Capital allocation and portfolio optimisation
AI	Research synthesis and orchestration
Verification	Independent consistency, contradiction and quality checks

The core principle is simple:

LLMs reason. Models calculate. Databases remember. Verification checks.

⸻

Universal Analytical Packet

All nine engines communicate using a shared contract called the Universal Analytical Packet (UAP) — every piece of output an engine produces, not just a final answer, is wrapped in one.

Each UAP carries:

* what kind of claim it is — FACT (directly observed), ESTIMATE (model output), or JUDGEMENT (interpretation of evidence)
* how much it's currently trusted — e.g. VERIFIED, PROVISIONAL, STALE, CONFLICTED, or REJECTED, which can change over time as new evidence arrives
* where it came from and when — source, producer, and separate timestamps for when something was observed, published, retrieved, and generated
* what it depends on — a traceable chain back to the evidence and upstream calculations it was built from

This is what stops a model's guess from quietly being presented as a fact, and what makes "why did the system say that?" answerable with a real, traceable chain of evidence rather than a plausible-sounding paragraph.

⸻

What's Implemented Today

OptiFi's engines are real, tested code, not placeholders — but the data they currently run on is synthetic, and no product surface exists yet. This is an honest breakdown, not a status page:

Implemented and tested
* All nine engines above exist as real Python packages with 600+ automated tests (unit, integration, and adversarial) passing across the repository.
* The UAP contract itself: provenance chains, validation-status propagation, revision/versioning (`supersede()`), and a look-ahead-contamination check that rejects a result depending on data it couldn't actually have had yet.
* A provider-agnostic data ingestion framework (`data-engine`): a `ProviderAdapter` interface any real vendor could plug into, acquisition and validation orchestration (staleness, duplicate, currency-mismatch, discontinuity, and calendar checks), and a deterministic local cache that replays any previously-ingested record byte-for-byte.
* A forecasting and evaluation layer (`forecast-engine` + `evaluation-engine`): several baselines (naive, historical mean, rolling mean, AR(1)) and two competing model families (a statistical and a lightweight ML model) per forecasting target, evaluated with strict walk-forward validation that never trains on future data. Forecasts are frozen once made, scored with target-appropriate metrics, and rolled up into auditable per-model scorecards that can retire an underperforming model automatically.
* Independent verification and disagreement-preserving synthesis logic that keeps model estimates and AI interpretations visibly distinct from verified facts, end to end.

Experimental / not yet connected
* No live market data. `data-engine`'s provider abstraction only has a deterministic fixture provider behind it — no Bloomberg, LSEG, or other paid/live feed is connected. Real vendor selection is a documented, open procurement decision (see `docs/DATA_SOURCE_REGISTRY.md`), not a technical blocker.
* All current forecasting examples run on synthetic data. The three demonstration targets (UK CPI inflation, a synthetic index's realised volatility, a synthetic company's revenue-growth direction) use fixed-seed, statistically realistic but fabricated series, clearly labelled as such in the code, because no real historical series is connected yet. Backtest results demonstrate the evaluation methodology, not real-world forecasting skill.
* The Financial Twin (a per-user financial-position model, described in `/docs`) and full AI CIO synthesis are specified but not yet built as running product code. An illustrative synthetic vertical-slice test wires every engine together end to end (`tests/integration/`) — but there is no deployed application, no user accounts, and no connection to anyone's real portfolio.

Explicitly out of scope right now
* Real-time data, live trading, or execution of any financial transaction.
* Personalised investment advice for a real user.
* Any claim that OptiFi's forecasts outperform real markets — nothing here has been evaluated against real market data yet.

⸻

Financial Twin (design concept — not yet implemented)

OptiFi is designed around a machine-readable representation of the user's financial position: investments, cash, liabilities, currency exposure, liquidity requirements, risk tolerance, investment horizon, and financial objectives, so market developments can be evaluated against a user's actual situation rather than in isolation. No per-user data model, storage, or account connection exists in the codebase yet — this is architecture, not a built feature.

⸻

Decision-Making Under Uncertainty

OptiFi is not built around the claim "this is what the market will do." Instead, it asks what futures are plausible, and what decisions remain sensible across them. Forecasts are designed to feed into scenarios and simulations before optimisation — the objective is robust decision-making, not perfect prediction.

⸻

MVP Scope (target, not yet a built product)

The intended MVP narrows this down considerably: a manually defined portfolio, equities and ETFs, portfolio analytics, a small set of macroeconomic indicators, financial news, forecasting, scenario simulation, optimisation, and AI-generated portfolio intelligence — answering one question: what are the three most important developments affecting my portfolio today? The engine layer described above is the foundation this would be built on; the end-to-end product experience itself does not exist yet.

⸻

Repository Structure

OptiFi/
├── data-engine/          ingestion, validation, provenance — implemented
├── forecast-engine/      baselines, models, ensembling — implemented
├── evaluation-engine/    forecast tracking, metrics, scorecards — implemented
├── causal-engine/        economic/financial relationship modelling — implemented
├── quant-engine/         portfolio analytics and risk — implemented
├── simulation-engine/    scenario generation and Monte Carlo — implemented
├── optimisation-engine/  capital allocation and optimisation — implemented
├── verification-engine/  independent consistency and quality checks — implemented
├── ai-engine/            research synthesis and orchestration — implemented
├── shared/               the UAP contract and cross-engine types
├── backend/              orchestration/API layer — placeholder
├── frontend/             user interface — placeholder
├── infrastructure/       deployment and operations — placeholder
├── research/             placeholder
├── scripts/              placeholder
├── tests/                cross-engine integration and adversarial tests
└── docs/                 specifications and architecture documents

For deeper technical documentation, see /docs. Recommended starting points: PRODUCT_VISION.md, SYSTEM_ARCHITECTURE.md, ENGINE_PIPELINE_SPECIFICATION.md, ANALYTICAL_CONTRACT_SPEC.md, VERIFICATION_FRAMEWORK.md.

⸻

Current Status & Roadmap

Now — nine specialist engines implemented and tested, communicating through the shared UAP contract. Data ingestion, forecasting, and evaluation infrastructure exist and run end to end against synthetic and fixture data.

Not yet — a connected live data vendor, a deployed backend/frontend, real user accounts or portfolios, or personalised recommendation generation.

Next — real vendor selection for market/macro data (a procurement decision, not a technical one), wiring the AI CIO synthesis layer to real rather than illustrative candidate generation, and a first thin end-to-end product slice.

OptiFi moves in discrete, documented phases — see /docs for the full specification set.

⸻

Disclaimer

OptiFi is experimental research software. It does not provide financial, investment, legal, or tax advice, does not connect to any real brokerage or bank account, and does not execute trades.

⸻

The goal is not to predict the future perfectly.
It is to make better financial decisions across plausible futures.
