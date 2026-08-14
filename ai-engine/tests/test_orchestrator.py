from datetime import datetime, timedelta, timezone

import pytest

from optifi_ai.explanation import UserSophistication
from optifi_ai.generator import StubExplanationGenerator
from optifi_ai.intent import SpecialistEngine
from optifi_ai.orchestrator import (
    build_complex_recession_pool,
    build_simple_allocation_pool,
    CIOOrchestrator,
    SpecialistOutputPool,
    UserQuery,
)
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

_NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)


def _cio() -> CIOOrchestrator:
    return CIOOrchestrator(StubExplanationGenerator())


def test_simple_query_only_touches_quant():
    pool = build_simple_allocation_pool(_NOW)
    routing, explanation = _cio().answer_query(
        UserQuery("What is my technology allocation?"), pool, _NOW, timedelta(days=30)
    )
    assert routing.engines == frozenset({SpecialistEngine.QUANT})
    assert explanation.facts  # the allocation fact reached the explanation
    assert explanation.roadblocks == []


def test_complex_query_calls_the_full_chain_and_produces_a_candidate():
    pool, candidate, verdicts = build_complex_recession_pool(_NOW)
    routing, explanation = _cio().answer_query(
        UserQuery("Should I reduce equities because recession risk has increased?"),
        pool,
        _NOW,
        timedelta(days=30),
        candidate=candidate,
        candidate_verdicts=verdicts,
    )
    assert routing.engines == frozenset(
        {
            SpecialistEngine.CAUSAL,
            SpecialistEngine.FORECAST,
            SpecialistEngine.SIMULATION,
            SpecialistEngine.QUANT,
            SpecialistEngine.OPTIMISATION,
            SpecialistEngine.VERIFICATION,
        }
    )
    # every specialist actually contributed real output, not a placeholder
    assert pool.by_engine[SpecialistEngine.CAUSAL]
    assert pool.by_engine[SpecialistEngine.FORECAST]
    assert pool.by_engine[SpecialistEngine.SIMULATION]
    assert pool.by_engine[SpecialistEngine.QUANT]
    assert pool.by_engine[SpecialistEngine.OPTIMISATION]
    assert candidate.subject in explanation.suggested_action


def test_missing_specialist_output_is_surfaced_as_a_roadblock_not_silently_dropped():
    pool = SpecialistOutputPool()  # empty — CAUSAL etc. never populated
    routing, explanation = _cio().answer_query(
        UserQuery("Should I reduce equities because recession risk has increased?"),
        pool,
        _NOW,
        timedelta(days=30),
    )
    missing_subjects = {r.subject for r in explanation.roadblocks if r.kind == "MISSING_DEPENDENCY"}
    assert SpecialistEngine.CAUSAL.value in missing_subjects
    assert SpecialistEngine.OPTIMISATION.value in missing_subjects


def test_optimisation_routed_without_a_candidate_is_its_own_roadblock():
    pool = SpecialistOutputPool()
    pool.add(
        SpecialistEngine.OPTIMISATION,
        [
            UAP(
                subject="irrelevant",
                information_class=InformationClass.ESTIMATE,
                validation_status=ValidationStatus.PROVISIONAL,
                result=1.0,
                source="s",
                producer="p",
                confidence=ConfidenceLevel.LOW,
            )
        ],
    )
    _routing, explanation = _cio().answer_query(
        UserQuery("should i rebalance"), pool, _NOW, timedelta(days=30)
    )
    assert any(
        "no candidate was supplied to the verification gate" in r.description for r in explanation.roadblocks
    )


def test_candidate_without_verdicts_is_rejected_outright():
    pool = SpecialistOutputPool()
    candidate = UAP(
        subject="candidate",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=1.0,
        source="s",
        producer="p",
        confidence=ConfidenceLevel.LOW,
    )
    with pytest.raises(ValueError):
        _cio().answer_query(
            UserQuery("should i rebalance"), pool, _NOW, timedelta(days=30), candidate=candidate
        )
