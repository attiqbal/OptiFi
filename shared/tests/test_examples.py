"""
Tests for the illustrative Sharpe-ratio UAP example.
"""

import pytest

from optifi_shared import ConfidenceLevel, InformationClass, ValidationStatus
from optifi_shared.examples import example_sharpe_ratio_uap


def test_example_sharpe_ratio_uap_computes_correct_result():
    uap = example_sharpe_ratio_uap(
        portfolio_return=0.08,
        risk_free_rate=0.03,
        portfolio_std_dev=0.12,
    )

    expected = (0.08 - 0.03) / 0.12
    assert uap.result == pytest.approx(expected)


def test_example_sharpe_ratio_uap_is_correctly_shaped():
    uap = example_sharpe_ratio_uap(
        portfolio_return=0.08,
        risk_free_rate=0.03,
        portfolio_std_dev=0.12,
    )

    assert uap.information_class == InformationClass.ESTIMATE
    assert uap.validation_status == ValidationStatus.PROVISIONAL
    assert uap.subject
    assert uap.source
    assert uap.producer
    assert uap.confidence == ConfidenceLevel.LOW
    assert uap.assumptions
    assert uap.limitations
