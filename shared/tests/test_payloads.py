"""
Tests for the typed engine-specific payload families (Phase E1
hardening).
"""

import pytest
from pydantic import ValidationError

from optifi_shared import (
    ConfidenceLevel,
    expect_payload,
    FailureResult,
    ForecastResult,
    FundamentalObservation,
    InformationClass,
    MacroObservation,
    MarketObservation,
    OptimisationResult,
    PortfolioAnalytics,
    RecommendationCandidate,
    RiskAnalytics,
    StructuredEvent,
    UAP,
    ValidationStatus,
)


def test_market_observation_constructs():
    obs = MarketObservation(instrument_id="AAPL", price=150.25, currency="USD")
    assert obs.instrument_id == "AAPL"
    assert obs.price == 150.25


def test_macro_observation_constructs_with_optional_unit_defaulted():
    obs = MacroObservation(indicator_name="UK CPI YoY", value=3.2)
    assert obs.unit is None


def test_fundamental_observation_constructs():
    obs = FundamentalObservation(issuing_entity_id="entity-1", metric_name="revenue", value=1_000_000.0)
    assert obs.metric_name == "revenue"


def test_structured_event_defaults_entity_ids_to_empty_list():
    event = StructuredEvent(event_type="rate_decision", description="BoE holds rates")
    assert event.entity_ids == []


def test_forecast_result_constructs_with_bounds():
    fr = ForecastResult(point_forecast=0.03, horizon="12-month", lower_bound=0.01, upper_bound=0.05)
    assert fr.lower_bound < fr.point_forecast < fr.upper_bound


def test_portfolio_analytics_constructs_with_breakdown():
    pa = PortfolioAnalytics(metric_name="sector exposure", value=100.0, breakdown={"tech": 40.0, "finance": 60.0})
    assert sum(pa.breakdown.values()) == 100.0


def test_risk_analytics_constructs():
    ra = RiskAnalytics(metric_name="parametric VaR", value=27914.09, confidence_level=0.95)
    assert ra.confidence_level == 0.95


def test_optimisation_result_constructs():
    opt = OptimisationResult(weights={"A": 0.6, "B": 0.4}, objective_value=0.025)
    assert sum(opt.weights.values()) == pytest.approx(1.0)


def test_recommendation_candidate_defaults_expected_impact_to_empty_dict():
    rc = RecommendationCandidate(action_description="reduce duration exposure")
    assert rc.expected_impact == {}


def test_failure_result_accepts_known_category():
    fr = FailureResult(category="MISSING_INPUT", message="expected_returns not supplied")
    assert fr.category == "MISSING_INPUT"


def test_failure_result_rejects_unknown_category():
    with pytest.raises(ValidationError, match="not one of AnalyticalFailure"):
        FailureResult(category="NOT_A_REAL_CATEGORY", message="x")


# --- typed payload mismatch (required test category #11) ---


def _make_uap_with_result(result) -> UAP:
    return UAP(
        subject="test subject",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=result,
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
    )


def test_expect_payload_returns_the_narrowed_value_on_a_correct_match():
    risk = RiskAnalytics(metric_name="VaR", value=1000.0)
    uap = _make_uap_with_result(risk)

    result = expect_payload(uap.result, RiskAnalytics)

    assert result is risk
    assert result.value == 1000.0


def test_expect_payload_raises_on_type_mismatch_not_a_silent_pass_through():
    """
    A receiver expecting RiskAnalytics but getting a different typed
    payload (OptimisationResult) must be told explicitly, not allowed to
    proceed as if it received what it expected.
    """
    wrong_payload = OptimisationResult(weights={"A": 1.0})
    uap = _make_uap_with_result(wrong_payload)

    with pytest.raises(TypeError, match="expected RiskAnalytics"):
        expect_payload(uap.result, RiskAnalytics)


def test_expect_payload_raises_on_raw_dict_instead_of_typed_payload():
    """The other direction of the same mismatch: a receiver expecting a
    typed payload but getting an untyped dict (the pre-Phase-E1 pattern
    every existing function still uses) must be told explicitly too."""
    uap = _make_uap_with_result({"value": 1000.0})

    with pytest.raises(TypeError, match="expected RiskAnalytics"):
        expect_payload(uap.result, RiskAnalytics)


def test_expect_payload_error_names_the_actual_type_received():
    uap = _make_uap_with_result(42.0)

    with pytest.raises(TypeError, match="got float"):
        expect_payload(uap.result, RiskAnalytics)
