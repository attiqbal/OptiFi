"""
No Hindsight Leakage — PHASE E5 Part 5, the centerpiece requirement:
"Build explicit automated tests that attempt to insert future
information. They must fail."

Every test in this file is a real ATTACK: it deliberately tries to get
future information into a snapshot, a decision package, or a model
scorecard selection, and asserts the attempt is rejected or excluded —
not merely that the happy path behaves. Several tests here reuse
`snapshot.py`/`decision_package.py` directly rather than re-deriving
their own logic, so a future change to the freeze mechanism that
weakens it would break these tests, not just the unit tests for the
mechanism itself.
"""

from datetime import datetime, timedelta, timezone

import pytest
from optifi_causal import CausalClaim, TransmissionGraph
from optifi_evaluation import build_scorecard
from optifi_forecast import exponential_smoothing_forecast
from optifi_quant import duration_price_sensitivity, SensitivityRegistry
from optifi_shared import (
    ConfidenceLevel,
    InformationClass,
    MacroObservation,
    UAP,
    UnsupportedFailure,
    ValidationStatus,
)
from optifi_simulation import propagate_scenario
from optifi_simulation.scenario_library import INFLATION_SURPRISE_1PP
from optifi_verification import check_no_look_ahead_contamination, VerdictType

from optifi_replay import build_snapshot, filter_available_scorecards, get_period
from optifi_replay.decision_package import run_replay

AS_OF = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _macro_uap(month: int, value: float, as_of_base: datetime = AS_OF) -> UAP:
    t = as_of_base - timedelta(days=365) + timedelta(days=30 * month)
    return UAP(
        subject="attack: macro indicator",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=MacroObservation(indicator_name="attack indicator", value=value, unit="%"),
        source="test",
        producer="test",
        confidence=ConfidenceLevel.MODERATE,
        observation_time=t,
        publication_time=t,
        retrieval_time=t,
    )


# --- Attack 1: directly inject a future-published fact into the candidate pool ---


def test_attack_inject_a_future_fact_directly_must_fail():
    genuinely_historical = [_macro_uap(m, 2.0 + 0.1 * m) for m in range(10)]
    attacker_injected_future_fact = UAP(
        subject="attack: leaked future fact",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=MacroObservation(indicator_name="leaked", value=999.0, unit="%"),
        source="attacker",
        producer="attacker",
        confidence=ConfidenceLevel.MODERATE,
        publication_time=AS_OF + timedelta(days=1),
        retrieval_time=AS_OF + timedelta(days=1),
    )
    snapshot = build_snapshot(AS_OF, genuinely_historical + [attacker_injected_future_fact])
    assert attacker_injected_future_fact.id not in {u.id for u in snapshot.available_uaps}
    assert 999.0 not in [u.result.value for u in snapshot.available_uaps if isinstance(u.result, MacroObservation)]


# --- Attack 2: relabel a future fact's timestamp to look historical (only
# --- catches HONEST metadata; documents a real, stated limit) ---


def test_attack_spoofed_early_publication_time_is_not_caught_by_timestamp_filtering_alone():
    """
    IMPORTANT, HONEST LIMITATION (Deliverable #10): `build_snapshot`
    trusts the `publication_time`/`retrieval_time` fields it is given —
    it has no independent way to verify a UAP's timestamp is genuine.
    An attacker (or a data-quality bug) that mislabels a UAP containing
    genuinely future-derived information with an early timestamp WILL
    pass this filter. This test documents that explicitly, rather than
    silently leaving it undiscovered, so it is not mistaken for a solved
    problem. Defense against this specific attack requires independent
    timestamp provenance verification, which is out of scope here — see
    the Phase E5 deliverable's own limitations.
    """
    spoofed = UAP(
        subject="attack: spoofed vintage",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=MacroObservation(indicator_name="spoofed", value=999.0, unit="%"),
        source="attacker",
        producer="attacker",
        confidence=ConfidenceLevel.MODERATE,
        publication_time=AS_OF - timedelta(days=1),  # falsely claims to predate as_of
        retrieval_time=AS_OF - timedelta(days=1),
    )
    snapshot = build_snapshot(AS_OF, [spoofed])
    # This DOES pass the filter — proving the limitation is real, not hypothetical.
    assert spoofed.id in {u.id for u in snapshot.available_uaps}


# --- Attack 3: force the forecast step to peek at future series values ---


def test_attack_forecast_computed_on_the_full_future_inclusive_series_diverges_from_the_real_replay():
    period = get_period("inflation_shock")
    package = run_replay(period)

    full_series = period.cpi_series()  # includes the "future" 6 months
    cheating_forecast = exponential_smoothing_forecast(full_series)  # peeks at everything

    # The real replay's forecast must NOT equal the cheating forecast
    # whenever they would genuinely differ (proving the replay's
    # forecast is NOT silently computed on the full series).
    truncated = full_series[: period.cpi_cutoff_month + 1]
    honest_forecast = exponential_smoothing_forecast(truncated)
    if honest_forecast != pytest.approx(cheating_forecast):
        assert package.forecast_uap.result != pytest.approx(cheating_forecast)
        assert package.forecast_uap.result == pytest.approx(honest_forecast)


# --- Attack 4: smuggle a future-dated dependency into a decision package's
# --- own dependency list and confirm the safety net (not just the builder) catches it ---


def test_attack_smuggled_future_dependency_in_known_packets_is_still_rejected():
    """Defense in depth: even if a future-dated UAP somehow made it into
    a decision package's dependency graph, the independent verification
    check (already run by `run_replay` itself) must still catch it —
    this proves the safety net is real, not merely that the builder
    happened to exclude it upstream."""
    graph = TransmissionGraph()
    claim = CausalClaim(
        subject="attack test",
        validation_status=ValidationStatus.PROVISIONAL,
        result="test",
        source="test",
        producer="test",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id="entity:uk-cpi-yoy",
        effect_entity_id="entity:duration-sensitive-assets",
        mechanism="test mechanism",
    )
    graph.add_edge(claim)
    registry = SensitivityRegistry()
    leaked_sensitivity = duration_price_sensitivity(modified_duration=7.0)
    leaked_sensitivity = leaked_sensitivity.model_copy(
        update={
            "result": {**leaked_sensitivity.result, "horizon": INFLATION_SURPRISE_1PP.horizon, "regime": None},
            "publication_time": AS_OF + timedelta(days=30),  # the attack: dated AFTER as_of
            "retrieval_time": AS_OF + timedelta(days=30),
        }
    )
    registry.register("entity:uk-cpi-yoy", "entity:duration-sensitive-assets", leaked_sensitivity)

    result = propagate_scenario(
        INFLATION_SURPRISE_1PP, "entity:duration-sensitive-assets", graph, registry, "entity:uk-cpi-yoy", as_of=AS_OF
    )
    known_packets = {leaked_sensitivity.id: leaked_sensitivity, claim.id: claim}
    verdict = check_no_look_ahead_contamination(result, known_packets)
    assert verdict.verdict_type == VerdictType.REJECT


# --- Attack 5: revised macro vintage published after T must not leak the revised value ---


def test_attack_revised_value_published_after_as_of_does_not_leak_into_the_snapshot():
    from optifi_shared import supersede

    advance = _macro_uap(0, 2.9, as_of_base=AS_OF)
    revision = UAP(
        subject=advance.subject,
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=MacroObservation(indicator_name="attack indicator", value=99.9, unit="%"),  # the "leaked" future revision
        source="test",
        producer="test",
        confidence=ConfidenceLevel.MODERATE,
        publication_time=AS_OF + timedelta(days=1),  # published AFTER as_of
        retrieval_time=AS_OF + timedelta(days=1),
    )
    revised_linked, advance_superseded = supersede(advance, revision)

    snapshot = build_snapshot(AS_OF, [advance_superseded, revised_linked])
    values = [u.result.value for u in snapshot.available_uaps if isinstance(u.result, MacroObservation)]
    assert 99.9 not in values
    assert 2.9 in values


# --- Attack 6: use a model scorecard evaluated after T ---


def test_attack_scorecard_evaluated_after_as_of_is_excluded_from_model_version_selection():
    window = (AS_OF - timedelta(days=365), AS_OF)
    stale_but_valid = build_scorecard(
        model_id="econometric-ses", model_version="v1", target="t", horizon="1-month",
        training_window=window, evaluation_period=window, primary_metric_name="MAE",
        primary_metric_value=0.2, higher_is_better=False, baseline_metric_value=0.3,
        n_evaluated=20, last_evaluation=AS_OF - timedelta(days=10), now=AS_OF,
    )
    future_evaluated = build_scorecard(
        model_id="econometric-ses", model_version="v2", target="t", horizon="1-month",
        training_window=window, evaluation_period=window, primary_metric_name="MAE",
        primary_metric_value=0.05, higher_is_better=False, baseline_metric_value=0.3,
        n_evaluated=50, last_evaluation=AS_OF + timedelta(days=5), now=AS_OF + timedelta(days=5),
    )
    available = filter_available_scorecards(AS_OF, [stale_but_valid, future_evaluated])
    versions = {s.model_version for s in available}
    assert "v2" not in versions  # the better-looking, not-yet-evaluated-at-T model must not appear
    assert "v1" in versions


def test_attack_bulk_scorecard_injection_all_future_are_excluded():
    window = (AS_OF - timedelta(days=365), AS_OF)
    future_scorecards = [
        build_scorecard(
            model_id=f"model-{i}", model_version="v1", target="t", horizon="1-month",
            training_window=window, evaluation_period=window, primary_metric_name="MAE",
            primary_metric_value=0.1, higher_is_better=False, baseline_metric_value=0.3,
            n_evaluated=20, last_evaluation=AS_OF + timedelta(days=i + 1), now=AS_OF + timedelta(days=i + 1),
        )
        for i in range(20)
    ]
    assert filter_available_scorecards(AS_OF, future_scorecards) == []


# --- Attack 7: as_of exactly equal to publication is allowed (boundary, not an attack) ---


def test_boundary_exactly_at_as_of_is_legitimately_available_not_a_false_positive():
    """Confirms the leakage tests above aren't succeeding merely because
    the filter is overly aggressive — a genuinely on-time fact must
    still be included."""
    on_time = _macro_uap(0, 2.9, as_of_base=AS_OF)
    on_time = on_time.model_copy(update={"publication_time": AS_OF, "retrieval_time": AS_OF})
    snapshot = build_snapshot(AS_OF, [on_time])
    assert on_time.id in {u.id for u in snapshot.available_uaps}
