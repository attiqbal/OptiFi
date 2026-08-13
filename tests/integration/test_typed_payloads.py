"""
Integration proof that typed payloads (Phase E1 hardening) compose
correctly with real engine output and a real UAP — not just isolated
type-construction tests. Deliberately does NOT modify any existing
engine function's return contract (quant-engine's parametric_var still
returns a bare float in .result, unchanged, per the Phase E1 deliverable's
migration notes) — this demonstrates the pattern a producer COULD use,
wrapping a real computed value, and a receiver genuinely consuming it via
expect_payload rather than parsing dict keys.
"""

from __future__ import annotations

from optifi_quant import parametric_var
from optifi_shared import ConfidenceLevel, expect_payload, InformationClass, RiskAnalytics, UAP, ValidationStatus


def test_real_quant_engine_output_wrapped_as_a_typed_payload_round_trips():
    var_uap = parametric_var(portfolio_value=1_000_000.0, portfolio_std_dev=0.15, confidence_level=0.95)

    # A producer choosing to expose this as a typed payload rather than
    # the bare float parametric_var itself still returns.
    typed_uap = UAP(
        subject=var_uap.subject,
        information_class=var_uap.information_class,
        validation_status=var_uap.validation_status,
        result=RiskAnalytics(metric_name="parametric VaR", value=var_uap.result, confidence_level=0.95),
        source=var_uap.source,
        producer=var_uap.producer,
        confidence=var_uap.confidence,
        dependencies=[var_uap.id],
    )

    # A receiver, without parsing dict keys or arbitrary prose.
    risk = expect_payload(typed_uap.result, RiskAnalytics)

    assert risk.value == var_uap.result
    assert risk.metric_name == "parametric VaR"
    assert risk.confidence_level == 0.95


def test_receiver_expecting_a_different_payload_type_is_told_explicitly():
    """
    A receiver written for RiskAnalytics must not silently misinterpret
    a differently-typed payload (or a plain float, the pre-Phase-E1
    shape parametric_var's own .result still has) as if it matched.
    """
    var_uap = parametric_var(portfolio_value=1_000_000.0, portfolio_std_dev=0.15, confidence_level=0.95)

    import pytest

    with pytest.raises(TypeError, match="expected RiskAnalytics"):
        expect_payload(var_uap.result, RiskAnalytics)
