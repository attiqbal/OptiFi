"""Part A: three targets, each genuinely justified, none chosen 'because
easy' (no assertion can directly test intent — this checks the concrete
shape: three distinct targets, one per category, each with real,
non-empty justification/data_note text)."""

from optifi_forecast import (
    ALL_TARGETS,
    COMPANY_REVENUE_DIRECTION_TARGET,
    MACRO_CPI_TARGET,
    MARKET_VOLATILITY_TARGET,
)


def test_exactly_three_targets_selected():
    assert len(ALL_TARGETS) == 3


def test_targets_are_distinct():
    assert len({t.target_id for t in ALL_TARGETS}) == 3
    assert len({t.subject for t in ALL_TARGETS}) == 3


def test_every_target_has_a_real_justification_and_data_note():
    for target in ALL_TARGETS:
        assert len(target.justification) > 100
        assert len(target.data_note) > 50
        assert target.horizon


def test_targets_cover_macro_market_and_company_categories():
    assert "CPI" in MACRO_CPI_TARGET.subject
    assert "volatility" in MARKET_VOLATILITY_TARGET.subject
    assert "revenue" in COMPANY_REVENUE_DIRECTION_TARGET.subject
