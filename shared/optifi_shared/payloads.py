"""
Typed engine-specific payload families — Phase E1 hardening.

Design objective (unchanged from the phase brief): a receiving engine
should know what kind of analytical object it received without parsing
arbitrary dictionaries or prose. The UAP envelope (`shared.uap`)
continues to carry every field common to all analytical output
(identity, classification, provenance, timing, uncertainty,
dependencies); the models below are what a producer MAY put into a
UAP's own `result` field instead of a raw dict/scalar, and what a
receiver can `isinstance()`-check against instead of inspecting keys.

Deliberately flat, not deeply inherited ("do not create unnecessary
inheritance complexity"): every payload below is a direct, sibling
`BaseModel` subclass with a handful of fields specific to its own
domain — there is no shared payload superclass carrying behaviour, only
a plain typing convention.

Two of the phase brief's named families are NOT defined here, because
this project already has a differently-shaped, already-implemented,
already-tested answer for them, predating this phase, and duplicating
that with a second, competing "nested payload" version would fragment
the codebase into two different typed-payload philosophies rather than
harden the existing one:

- **CausalAnalysis** — already `causal-engine`'s `CausalClaim`, a `UAP`
  SUBCLASS (not a `result`-nested payload) adding `cause_entity_id`,
  `effect_entity_id`, `mechanism`, `historical_precedent`, etc. directly
  as top-level fields (`causal-engine/optifi_causal/causal_claim.py`).
- **ScenarioResult** — already `simulation-engine`'s `ScenarioResult`,
  the identical name the phase brief itself uses, likewise a `UAP`
  subclass (`simulation-engine/optifi_simulation/scenario_result.py`).
- **VerificationResult** — already verification-engine's `Verdict`
  (`verification-engine/optifi_verification/verdict.py`): `verdict_type`,
  `reasons`, `failure_category`, `flagged_status`. Verification checks
  currently return a bare `Verdict`, not a UAP-wrapped one — that is an
  existing, separate design point (see the Phase E1 deliverable's
  migration notes), not something this module changes.

Migration scope, stated plainly: this module defines the ten remaining
families below and makes them real, tested, and usable. It does NOT
retrofit every existing engine function's return type onto them —
several existing functions' `result` fields (e.g. quant-engine's
`parametric_var`, whose `.result` is a bare float consumed as such by
several OTHER already-shipped functions across three packages) are
consumed as raw values in enough places that changing their shape would
be a wide, breaking, multi-package change of the same kind Section 3's
provenance-mandate fork is — deliberately out of scope for a single
additive hardening pass. See the deliverable's migration notes for the
full list of what remains unmigrated and why.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MarketObservation(BaseModel):
    """A single market/pricing data point (equity, ETF, bond, FX,
    commodity — DATA_SOURCE_REGISTRY.md Category A)."""

    instrument_id: str = Field(..., description="Stable identifier for the priced instrument.")
    price: float = Field(..., description="The observed price.")
    currency: str = Field(..., description="ISO-style currency code the price is denominated in.")


class MacroObservation(BaseModel):
    """A single macroeconomic indicator reading (DATA_SOURCE_REGISTRY.md
    Category B — rates, inflation, GDP, employment, yield curves)."""

    indicator_name: str = Field(..., description="e.g. 'UK CPI YoY', 'US 10Y yield'.")
    value: float
    unit: str | None = Field(default=None, description="e.g. '%', 'index points'.")


class FundamentalObservation(BaseModel):
    """A single company-fundamentals data point (DATA_SOURCE_REGISTRY.md
    Category C — earnings, financial statements, filings)."""

    issuing_entity_id: str = Field(..., description="ECONOMIC_ONTOLOGY.md issuing-entity identifier.")
    metric_name: str = Field(..., description="e.g. 'revenue', 'EPS', 'net debt'.")
    value: float
    unit: str | None = None


class StructuredEvent(BaseModel):
    """A discrete structured event extracted from unstructured text or a
    structured feed (corporate action, policy announcement, guidance
    change) — DATA_SOURCE_REGISTRY.md Category D/E."""

    event_type: str = Field(..., description="e.g. 'earnings_release', 'rate_decision', 'M&A_announcement'.")
    description: str
    entity_ids: list[str] = Field(default_factory=list, description="ECONOMIC_ONTOLOGY.md entities this event concerns.")


class ForecastResult(BaseModel):
    """A single forecast output (forecast-engine)."""

    point_forecast: float
    horizon: str = Field(..., description="e.g. '3-month', '12-month'.")
    lower_bound: float | None = Field(default=None, description="Lower bound of the forecast's uncertainty interval.")
    upper_bound: float | None = Field(default=None, description="Upper bound of the forecast's uncertainty interval.")


class PortfolioAnalytics(BaseModel):
    """A single portfolio-analytics figure (quant-engine, Stage 8 —
    holdings totals, allocation breakdowns)."""

    metric_name: str = Field(..., description="e.g. 'total value', 'sector exposure'.")
    value: float
    breakdown: dict[str, float] | None = Field(
        default=None, description="Optional finer-grained split (e.g. by asset, by sector)."
    )


class RiskAnalytics(BaseModel):
    """A single risk-measurement figure (quant-engine, Section 5.3 — VaR,
    volatility, beta, drawdown)."""

    metric_name: str = Field(..., description="e.g. 'parametric VaR', 'annualised volatility', 'beta'.")
    value: float
    confidence_level: float | None = Field(
        default=None, description="For confidence-level-dependent metrics (e.g. VaR); None where not applicable."
    )


class OptimisationResult(BaseModel):
    """A single portfolio-optimisation outcome (optimisation-engine,
    Section 5)."""

    weights: dict[str, float] = Field(..., description="Per-asset portfolio weights.")
    objective_value: float | None = Field(
        default=None, description="The solver's own objective value at the returned weights (e.g. portfolio variance)."
    )


class RecommendationCandidate(BaseModel):
    """A single candidate action framed for the user (ai-engine, Stage
    10) — figures only; narrative text belongs in the UAP's own
    `result` narrative fields elsewhere, not duplicated here."""

    action_description: str
    expected_impact: dict[str, float] = Field(
        default_factory=dict, description="e.g. {'expected_risk_reduction_pct': 3.2}."
    )


class FailureResult(BaseModel):
    """
    A structured analytical failure returned as a VALUE rather than
    raised as an exception — useful when a caller wants to collect
    failures without aborting control flow (e.g. one item's failure
    within a larger batch, or a Verdict-shaped 'this candidate could not
    be answered' record). Mirrors `optifi_shared.AnalyticalFailure`'s own
    category taxonomy (`shared/optifi_shared/failures.py`) so the two
    stay consistent — `category` is checked against that same set of
    strings, not a separate, competing list.
    """

    category: str = Field(..., description="One of AnalyticalFailure's category values.")
    message: str

    _VALID_CATEGORIES = frozenset(
        {
            "MISSING_INPUT",
            "STALE_INPUT",
            "CONFLICTED_INPUT",
            "INSUFFICIENT_DATA",
            "UNSUPPORTED",
            "OUT_OF_DISTRIBUTION",
            "MODEL_FAILURE",
            "VERIFICATION_FAILURE",
            # Phase E2 additions — raw-data-quality categories, see
            # failures.py's own "Phase E2 additions" section for why
            # these are distinct from the eight analytical categories
            # above rather than force-fit into one of them.
            "DUPLICATE_OBSERVATION",
            "CURRENCY_MISMATCH",
            "DISCONTINUITY",
            "TIMESTAMP_INCONSISTENCY",
            "CALENDAR_MISMATCH",
            "IMPOSSIBLE_VALUE",
        }
    )

    def model_post_init(self, __context) -> None:
        if self.category not in self._VALID_CATEGORIES:
            raise ValueError(
                f"FailureResult: category ({self.category!r}) is not one "
                f"of AnalyticalFailure's known categories: "
                f"{sorted(self._VALID_CATEGORIES)}."
            )


def expect_payload(result: object, payload_type: type[BaseModel]) -> BaseModel:
    """
    Confirms `result` (typically a UAP's own `.result`) is genuinely an
    instance of `payload_type`, and returns it narrowed to that type —
    the receiving-engine half of "should know what kind of analytical
    object it received without parsing arbitrary dictionaries." Raises
    `TypeError`, naming both the expected and actual type, rather than
    letting a receiver silently proceed against the wrong shape (e.g.
    attribute-accessing a plain dict and getting a confusing
    `AttributeError` several lines later, or — worse — a dict that
    happens to have a similarly-named key succeeding by coincidence).
    """
    if not isinstance(result, payload_type):
        raise TypeError(
            f"expect_payload: expected {payload_type.__name__}, got "
            f"{type(result).__name__} ({result!r})."
        )
    return result
