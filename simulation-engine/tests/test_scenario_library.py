"""
Tests for the scenario library — PHASE E4 Part 6: "a limited initial
scenario library... not hundreds of scenarios."
"""

import pytest

from optifi_simulation import get_scenario, SCENARIO_LIBRARY


def test_library_is_small_not_hundreds():
    assert 1 <= len(SCENARIO_LIBRARY) <= 15


def test_library_covers_every_named_category_exactly_once():
    expected_families = {"rates", "inflation", "recession", "equity_shock", "fx", "commodity", "earnings"}
    actual_families = {s.family for s in SCENARIO_LIBRARY}
    assert actual_families == expected_families
    # exactly one preset per family — a curated set, not a sprawling one.
    assert len(SCENARIO_LIBRARY) == len(expected_families)


def test_every_scenario_has_a_unique_id():
    ids = [s.scenario_id for s in SCENARIO_LIBRARY]
    assert len(ids) == len(set(ids))


def test_every_scenario_has_a_real_justification():
    for scenario in SCENARIO_LIBRARY:
        assert len(scenario.justification) > 40
        assert scenario.horizon
        assert scenario.perturbed_entity_id.startswith("entity:")


def test_get_scenario_returns_the_matching_definition():
    scenario = get_scenario("rates_cut_100bp")
    assert scenario.family == "rates"
    assert scenario.perturbation_magnitude == -100.0


def test_get_scenario_unknown_id_raises_key_error():
    with pytest.raises(KeyError):
        get_scenario("not_a_real_scenario_id")
