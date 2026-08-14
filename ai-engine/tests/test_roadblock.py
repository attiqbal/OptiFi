from datetime import datetime, timedelta, timezone

from optifi_ai.intent import SpecialistEngine
from optifi_ai.roadblock import check_staleness, detect_missing_dependencies, Roadblock
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus


def _uap(subject: str, **overrides) -> UAP:
    defaults = dict(
        subject=subject,
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result=1.0,
        source="test",
        producer="test",
        confidence=ConfidenceLevel.MODERATE,
    )
    defaults.update(overrides)
    return UAP(**defaults)


def test_missing_dependency_detected_for_each_required_but_unavailable_engine():
    required = frozenset({SpecialistEngine.QUANT, SpecialistEngine.CAUSAL})
    available = frozenset({SpecialistEngine.QUANT})
    roadblocks = detect_missing_dependencies(required, available)
    assert len(roadblocks) == 1
    assert roadblocks[0].kind == "MISSING_DEPENDENCY"
    assert roadblocks[0].subject == "CAUSAL"


def test_no_roadblock_when_everything_required_is_available():
    required = frozenset({SpecialistEngine.QUANT})
    available = frozenset({SpecialistEngine.QUANT, SpecialistEngine.CAUSAL})
    assert detect_missing_dependencies(required, available) == []


def test_stale_uap_is_flagged_against_present_time():
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    old = _uap("old fact", generated_at=now - timedelta(days=100))
    roadblocks = check_staleness([old], now, max_age=timedelta(days=30))
    assert len(roadblocks) == 1
    assert roadblocks[0].kind == "STALE_DATA"
    assert roadblocks[0].subject == "old fact"


def test_fresh_uap_is_not_flagged():
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    fresh = _uap("fresh fact", generated_at=now - timedelta(days=1))
    assert check_staleness([fresh], now, max_age=timedelta(days=30)) == []


def test_uap_with_no_time_field_is_not_assumed_stale_or_fresh():
    # generated_at always defaults on construction, so force it absent to
    # exercise the "cannot be checked" path explicitly.
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    u = _uap("untimed").model_copy(update={"generated_at": None})
    assert check_staleness([u], now, max_age=timedelta(days=1)) == []


def test_max_age_has_no_hardcoded_default_and_must_be_supplied():
    # This is a signature assertion, not a behavioural one — see
    # roadblock.py's module docstring on why no default is provided.
    import inspect

    sig = inspect.signature(check_staleness)
    assert sig.parameters["max_age"].default is inspect.Parameter.empty
