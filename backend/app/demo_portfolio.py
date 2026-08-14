"""
demo_portfolio.py — the one illustrative demo dataset every backend route
renders. Built the same way replay-engine/the vertical slice/E6's
CIOOrchestrator worked examples build theirs: real function calls over
small, fixed, clearly-labelled synthetic series, never random and never a
hand-typed "just for the UI" number. No live vendor, no real user account —
see README.md's existing scope statement.

Two named variants, selected by the caller (never per-request randomness):
"default" has two real opportunities (idle cash above the liquidity target,
technology exposure above its target maximum); "efficient" sits within
every target, giving a genuine, non-fabricated "no opportunities" state.

Portfolio totals deliberately reuse APP_UX_BLUEPRINT.md Section 7's own
worked example (£548,600 assets, £120,000 liabilities, £428,600 net) for
continuity with the spec this UI implements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from optifi_causal import CausalClaim, TransmissionGraph
from optifi_optimisation import maximum_sharpe_ratio
from optifi_quant import (
    cash_efficiency,
    composite_capital_efficiency_score,
    covariance_matrix,
    debt_efficiency,
    duration_price_sensitivity,
    estimate_factor_sensitivity,
    historical_var,
    investment_efficiency,
    liquidity_efficiency,
    parametric_var,
    portfolio_variance,
    propagate_to_portfolio,
    risk_efficiency,
    sharpe_ratio,
    tax_efficiency,
    SensitivityRegistry,
)
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_simulation import propagate_scenario
from optifi_simulation.scenario_library import RATES_CUT_100BP

ASSETS_TOTAL = 548_600.0
LIABILITIES_TOTAL = 120_000.0
NET_CAPITAL = ASSETS_TOTAL - LIABILITIES_TOTAL

TECH_TARGET_MAX = 0.25
LIQUIDITY_TARGET_FRACTION = 0.10
RISK_TARGET_GBP = 14_000.0  # illustrative Mandate risk tolerance, parametric-VaR units
RISK_FREE_RATE_MONTHLY = 0.0015
MAX_SINGLE_PERIOD_LOSS = ASSETS_TOTAL * 0.10
CONFIDENCE_LEVEL = 0.95

MORTGAGE_BALANCE = LIABILITIES_TOTAL
MORTGAGE_RATE = 0.045

UK_BANK = "entity:uk-bank-equity"
UK_GILTS = "entity:uk-gilts"
US_TECH = "entity:us-tech-equity"
EU_INDUSTRIAL = "entity:eu-industrial-equity"
CASH_GBP = "entity:cash-gbp"
UK_BASE_RATE = "entity:uk-base-rate"

HOLDING_META = {
    UK_BANK: {"label": "UK Banks", "sector": "Financials", "geography": "UK", "currency": "GBP"},
    UK_GILTS: {"label": "UK Gilts", "sector": "Government Bonds", "geography": "UK", "currency": "GBP"},
    US_TECH: {"label": "US Technology", "sector": "Technology", "geography": "US", "currency": "USD"},
    EU_INDUSTRIAL: {"label": "EU Industrials", "sector": "Industrials", "geography": "EU", "currency": "EUR"},
    CASH_GBP: {"label": "GBP Cash", "sector": "Cash", "geography": "UK", "currency": "GBP"},
}

# Small, fixed, illustrative synthetic monthly return series — not fitted
# to any real history, not random. Same discipline as
# orchestrator.py's/replay-engine's own synthetic fixtures.
RETURNS_BY_ENTITY = {
    UK_BANK: [0.01, -0.005, 0.02, 0.00, 0.015, -0.01, 0.005, 0.02, -0.015, 0.01, 0.00, 0.025],
    UK_GILTS: [0.002, 0.001, -0.003, 0.004, 0.000, 0.002, -0.001, 0.003, 0.001, -0.002, 0.002, 0.001],
    US_TECH: [0.03, -0.02, 0.04, 0.01, -0.03, 0.05, 0.02, -0.01, 0.03, 0.00, -0.02, 0.04],
    EU_INDUSTRIAL: [0.015, 0.005, -0.01, 0.02, 0.00, 0.01, -0.005, 0.015, 0.005, -0.01, 0.02, 0.00],
    CASH_GBP: [0.0015] * 12,
}
# Illustrative UK base-rate path (percentage points), paired with UK_BANK's
# returns above to estimate a real (not asserted) factor sensitivity.
_UK_BASE_RATE_HISTORY = [5.25, 5.25, 5.00, 5.00, 4.75, 4.75, 4.75, 4.50, 4.50, 4.50, 4.25, 4.25]

WEIGHTS_BY_VARIANT: dict[str, dict[str, float]] = {
    "default": {UK_BANK: 0.20, UK_GILTS: 0.20, US_TECH: 0.28, EU_INDUSTRIAL: 0.17, CASH_GBP: 0.15},
    "efficient": {UK_BANK: 0.24, UK_GILTS: 0.28, US_TECH: 0.18, EU_INDUSTRIAL: 0.20, CASH_GBP: 0.10},
}


def _fact(subject: str, result, producer: str, now: datetime, **kw) -> UAP:
    return UAP(
        subject=subject,
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=result,
        source="illustrative demo portfolio — not a real user account",
        producer=producer,
        confidence=kw.pop("confidence", ConfidenceLevel.HIGH),
        generated_at=now,
        **kw,
    )


@dataclass
class Holding:
    entity_id: str
    label: str
    sector: str
    geography: str
    currency: str
    weight: float
    value: float
    fact_uap: UAP


@dataclass
class DemoPortfolio:
    variant: str
    now: datetime
    holdings: list[Holding]
    assets_total: float
    liabilities_total: float
    net_capital: float
    mortgage_uap: UAP
    stale_price_check_uap: UAP
    covariance_uap: UAP
    variance_uap: UAP
    historical_var_uap: UAP
    parametric_var_uap: UAP
    sharpe_uap: UAP
    capital_efficiency_uap: UAP
    sub_efficiency_uaps: dict[str, UAP]
    causal_claims: list[CausalClaim]
    rate_cut_scenario_results: dict[str, UAP]
    rate_sensitive_impact_uap: UAP
    all_uaps: dict[str, UAP] = field(default_factory=dict)

    def register(self, *uaps: UAP) -> None:
        for u in uaps:
            self.all_uaps[u.id] = u


def build_demo(variant: str, now: datetime) -> DemoPortfolio:
    if variant not in WEIGHTS_BY_VARIANT:
        raise ValueError(f"build_demo: unknown variant {variant!r} — known: {list(WEIGHTS_BY_VARIANT)}")
    weights = WEIGHTS_BY_VARIANT[variant]

    holdings = []
    for entity_id, meta in HOLDING_META.items():
        weight = weights[entity_id]
        value = weight * ASSETS_TOTAL
        fact_uap = _fact(
            f"holding: {meta['label']}",
            {"entity_id": entity_id, "value": value, "weight": weight, **meta},
            "demo-portfolio (illustrative holdings, not a real account)",
            now,
        )
        holdings.append(
            Holding(entity_id, meta["label"], meta["sector"], meta["geography"], meta["currency"], weight, value, fact_uap)
        )

    mortgage_uap = _fact(
        "liability: residential mortgage",
        {"balance": MORTGAGE_BALANCE, "rate": MORTGAGE_RATE},
        "demo-portfolio (illustrative liability, not a real account)",
        now,
    )

    # Deliberately stale: an independent price checkpoint from well
    # outside any reasonable freshness window, so "stale data" is a real,
    # exercisable state (roadblock.check_staleness) rather than only
    # asserted in a unit test.
    stale_price_check_uap = _fact(
        "last independently verified price checkpoint: EU Industrials",
        {"entity_id": EU_INDUSTRIAL, "checked_days_ago": 100},
        "demo-portfolio (illustrative, deliberately stale)",
        now - timedelta(days=100),
    )

    cov_uap = covariance_matrix({e: r for e, r in RETURNS_BY_ENTITY.items()})
    variance_uap = portfolio_variance(weights, cov_uap.result)
    std_dev = variance_uap.result**0.5

    portfolio_monthly_returns = [
        sum(weights[e] * RETURNS_BY_ENTITY[e][i] for e in RETURNS_BY_ENTITY) for i in range(len(RETURNS_BY_ENTITY[UK_BANK]))
    ]
    hist_var_uap = historical_var(portfolio_monthly_returns, CONFIDENCE_LEVEL)
    param_var_uap = parametric_var(ASSETS_TOTAL, std_dev, CONFIDENCE_LEVEL)
    expected_returns = {e: sum(r) / len(r) for e, r in RETURNS_BY_ENTITY.items()}
    portfolio_return = sum(weights[e] * expected_returns[e] for e in weights)
    sharpe_uap = sharpe_ratio(portfolio_return, RISK_FREE_RATE_MONTHLY, std_dev)

    max_sharpe_frontier_uap = maximum_sharpe_ratio(
        expected_returns=expected_returns,
        covariance=cov_uap.result,
        risk_free_rate=RISK_FREE_RATE_MONTHLY,
        portfolio_value=ASSETS_TOTAL,
        max_single_period_loss=MAX_SINGLE_PERIOD_LOSS,
        confidence_level=CONFIDENCE_LEVEL,
        covariance_source_id=cov_uap.id,
    )
    # investment_efficiency expects a UAP whose .result is the plain
    # Sharpe-ratio float itself (QUANT_ENGINE_SPEC.md Section 7), not the
    # frontier point's full {weights, sharpe_ratio, ...} dict.
    max_sharpe_uap = UAP(
        subject="maximum achievable Sharpe ratio on the efficient frontier",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=max_sharpe_frontier_uap.result["sharpe_ratio"],
        source="derived from optimisation-engine's efficient-frontier computation",
        producer="optimisation-engine / maximum_sharpe_ratio, OPTIMISATION_ENGINE_SPEC.md Section 5.2",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=[max_sharpe_frontier_uap.id],
    )

    actual_cash = holdings[[h.entity_id for h in holdings].index(CASH_GBP)].value
    minimum_cash_reserve = ASSETS_TOTAL * LIQUIDITY_TARGET_FRACTION
    # Cash/debt efficiency mix annualised illustrative yields with the
    # monthly-return machinery used everywhere else above — an explicit,
    # illustrative-only simplification (not internally rescaled), same
    # honesty discipline QUANT_ENGINE_SPEC.md itself applies to its own
    # placeholder constants.
    sub_uaps = {
        "cash_efficiency": cash_efficiency(achieved_yield_on_cash=0.018, best_available_comparable_yield=0.045),
        "debt_efficiency": debt_efficiency(effective_borrowing_cost=MORTGAGE_RATE, risk_adjusted_expected_return=0.06),
        "risk_efficiency": risk_efficiency(ASSETS_TOTAL, std_dev, CONFIDENCE_LEVEL, RISK_TARGET_GBP),
        "tax_efficiency": tax_efficiency(tax_advantaged_allocation_used=45_000.0, tax_advantaged_allocation_available=60_000.0),
        "liquidity_efficiency": liquidity_efficiency(actual_cash, minimum_cash_reserve),
        "investment_efficiency": investment_efficiency(portfolio_return, RISK_FREE_RATE_MONTHLY, std_dev, max_sharpe_uap),
    }
    composite_uap = composite_capital_efficiency_score(
        sub_uaps["cash_efficiency"],
        sub_uaps["debt_efficiency"],
        sub_uaps["risk_efficiency"],
        sub_uaps["tax_efficiency"],
        sub_uaps["liquidity_efficiency"],
        sub_uaps["investment_efficiency"],
    )

    # === Causal pathway + scenario: "UK interest-rate expectations
    # changed" (RATES_CUT_100BP), over the two rate-sensitive holdings
    # only — propagate_to_portfolio refuses to fabricate coverage for
    # holdings that were never modelled (UnsupportedFailure), so this
    # view is explicitly scoped to what was actually computed. ===
    graph = TransmissionGraph()
    gilts_claim = CausalClaim(
        subject="UK base rate -> UK Gilts",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A UK base rate cut is associated with UK Gilt price appreciation",
        source="illustrative — not a real data source",
        producer="causal-engine (illustrative demo)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=UK_BASE_RATE,
        effect_entity_id=UK_GILTS,
        mechanism="Lower policy rates reduce yields, and bond prices move inversely to yields.",
        publication_time=now,
        retrieval_time=now,
    )
    bank_claim = CausalClaim(
        subject="UK base rate -> UK Banks",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A UK base rate cut is associated with narrower UK bank net interest margins",
        source="illustrative — not a real data source",
        producer="causal-engine (illustrative demo)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id=UK_BASE_RATE,
        effect_entity_id=UK_BANK,
        mechanism="Bank profitability partly depends on the spread between lending and deposit rates, which narrows as policy rates fall.",
        publication_time=now,
        retrieval_time=now,
    )
    graph.add_edges([gilts_claim, bank_claim])

    registry = SensitivityRegistry()
    _gilt_sensitivity_raw = duration_price_sensitivity(modified_duration=7.0)
    gilt_sensitivity = _gilt_sensitivity_raw.model_copy(
        update={
            "result": {**_gilt_sensitivity_raw.result, "horizon": RATES_CUT_100BP.horizon, "regime": None},
            "publication_time": now,
            "retrieval_time": now,
        }
    )
    registry.register(UK_BASE_RATE, UK_GILTS, gilt_sensitivity)

    rate_changes = [b - a for a, b in zip(_UK_BASE_RATE_HISTORY, _UK_BASE_RATE_HISTORY[1:])]
    bank_returns = RETURNS_BY_ENTITY[UK_BANK][: len(rate_changes)]
    bank_sensitivity = estimate_factor_sensitivity(
        UK_BASE_RATE, UK_BANK, rate_changes, bank_returns,
        horizon=RATES_CUT_100BP.horizon, regime=None, min_observations=min(10, len(rate_changes)),
    ).model_copy(update={"publication_time": now, "retrieval_time": now})
    registry.register(UK_BASE_RATE, UK_BANK, bank_sensitivity)

    scenario_results = {
        UK_GILTS: propagate_scenario(RATES_CUT_100BP, UK_GILTS, graph, registry, UK_BASE_RATE, as_of=now),
        UK_BANK: propagate_scenario(RATES_CUT_100BP, UK_BANK, graph, registry, UK_BASE_RATE, as_of=now),
    }
    rate_sensitive_weights = {
        UK_GILTS: weights[UK_GILTS] / (weights[UK_GILTS] + weights[UK_BANK]),
        UK_BANK: weights[UK_BANK] / (weights[UK_GILTS] + weights[UK_BANK]),
    }
    rate_sensitive_impact = propagate_to_portfolio(list(scenario_results.values()), rate_sensitive_weights)

    demo = DemoPortfolio(
        variant=variant,
        now=now,
        holdings=holdings,
        assets_total=ASSETS_TOTAL,
        liabilities_total=LIABILITIES_TOTAL,
        net_capital=NET_CAPITAL,
        mortgage_uap=mortgage_uap,
        stale_price_check_uap=stale_price_check_uap,
        covariance_uap=cov_uap,
        variance_uap=variance_uap,
        historical_var_uap=hist_var_uap,
        parametric_var_uap=param_var_uap,
        sharpe_uap=sharpe_uap,
        capital_efficiency_uap=composite_uap,
        sub_efficiency_uaps=sub_uaps,
        causal_claims=[gilts_claim, bank_claim],
        rate_cut_scenario_results=scenario_results,
        rate_sensitive_impact_uap=rate_sensitive_impact,
    )
    demo.register(
        *[h.fact_uap for h in holdings],
        mortgage_uap, stale_price_check_uap, cov_uap, variance_uap, hist_var_uap, param_var_uap, sharpe_uap,
        max_sharpe_frontier_uap, max_sharpe_uap, composite_uap, *sub_uaps.values(),
        gilts_claim, bank_claim, gilt_sensitivity, bank_sensitivity,
        *scenario_results.values(), rate_sensitive_impact,
    )
    return demo
