"""
Tests for build_snapshot — PHASE E5 Part 1 (freeze the information
universe) and the core of Part 5 ("No Hindsight Leakage... Build
explicit automated tests that attempt to insert future information.
They must fail.").
"""

from datetime import datetime, timedelta, timezone

import pytest
from optifi_shared import (
    ConfidenceLevel,
    InformationClass,
    MacroObservation,
    supersede,
    UAP,
    ValidationStatus,
)

from optifi_replay import build_snapshot

AS_OF = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _uap(subject: str, publication_time: datetime | None, retrieval_time: datetime | None = None, **overrides) -> UAP:
    defaults = dict(
        subject=subject,
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.VERIFIED,
        result="test",
        source="test",
        producer="test",
        confidence=ConfidenceLevel.MODERATE,
        publication_time=publication_time,
        retrieval_time=retrieval_time or publication_time,
    )
    defaults.update(overrides)
    return UAP(**defaults)


# --- basic availability filtering ---


def test_uap_published_before_as_of_is_available():
    uap = _uap("subject-a", publication_time=AS_OF - timedelta(days=1))
    snapshot = build_snapshot(AS_OF, [uap])
    assert uap.id in {u.id for u in snapshot.available_uaps}


def test_uap_published_exactly_at_as_of_is_available():
    uap = _uap("subject-a", publication_time=AS_OF)
    snapshot = build_snapshot(AS_OF, [uap])
    assert uap.id in {u.id for u in snapshot.available_uaps}


# --- Testing Requirement (Part 5): future information must be excluded ---


def test_uap_published_after_as_of_is_excluded_not_available():
    """The central hindsight-leakage test: attempting to include
    future-published information — it must fail to appear."""
    future_uap = _uap("subject-a", publication_time=AS_OF + timedelta(days=1))
    snapshot = build_snapshot(AS_OF, [future_uap])
    assert future_uap.id not in {u.id for u in snapshot.available_uaps}
    assert future_uap.id in {u.id for u in snapshot.excluded_future}


def test_uap_retrieved_after_as_of_even_if_published_before_is_excluded():
    """Genuinely available means OptiFi actually HAD it by T — publication
    alone isn't enough if OptiFi didn't retrieve it until later."""
    uap = _uap("subject-a", publication_time=AS_OF - timedelta(days=10), retrieval_time=AS_OF + timedelta(hours=1))
    snapshot = build_snapshot(AS_OF, [uap])
    assert uap.id not in {u.id for u in snapshot.available_uaps}
    assert uap.id in {u.id for u in snapshot.excluded_future}


def test_mixed_batch_only_excludes_the_future_ones():
    past = _uap("subject-a", publication_time=AS_OF - timedelta(days=1))
    future = _uap("subject-b", publication_time=AS_OF + timedelta(days=1))
    snapshot = build_snapshot(AS_OF, [past, future])
    available_ids = {u.id for u in snapshot.available_uaps}
    assert past.id in available_ids
    assert future.id not in available_ids


def test_uap_with_no_timestamps_is_excluded_as_unverifiable_not_assumed_safe():
    """Cannot prove it was available at T -> conservatively excluded,
    never silently assumed accessible."""
    untimed = _uap("subject-a", publication_time=None, retrieval_time=None)
    snapshot = build_snapshot(AS_OF, [untimed])
    assert untimed.id not in {u.id for u in snapshot.available_uaps}
    assert untimed.id in {u.id for u in snapshot.excluded_unverifiable}


def test_a_hundred_future_uaps_are_all_excluded():
    """Not just a single-item check — a real attempted bulk leakage."""
    future_uaps = [_uap(f"subject-{i}", publication_time=AS_OF + timedelta(days=i + 1)) for i in range(100)]
    snapshot = build_snapshot(AS_OF, future_uaps)
    assert len(snapshot.available_uaps) == 0
    assert len(snapshot.excluded_future) == 100


# --- vintage resolution + historical status reconstruction ---


def test_only_advance_estimate_available_when_revision_is_still_future():
    advance = _uap(
        "macro indicator: CPI",
        publication_time=AS_OF - timedelta(days=30),
        result=MacroObservation(indicator_name="CPI", value=2.9, unit="%"),
        vintage="advance estimate",
    )
    revised_linked, advance_superseded = supersede(
        advance,
        _uap(
            "macro indicator: CPI",
            publication_time=AS_OF + timedelta(days=5),  # revision published AFTER as_of
            result=MacroObservation(indicator_name="CPI", value=3.1, unit="%"),
            vintage="second estimate",
        ),
    )
    snapshot = build_snapshot(AS_OF, [advance, revised_linked])

    assert len(snapshot.available_uaps) == 1
    selected = snapshot.available_uaps[0]
    assert selected.result.value == 2.9
    assert selected.vintage == "advance estimate"


def test_historical_status_reconstructed_to_verified_when_superseding_was_still_future():
    """The subtle case: today's store marks the advance estimate
    SUPERSEDED (because it since HAS been revised), but at T, from
    OptiFi's own knowledge, no revision had happened yet — reporting
    SUPERSEDED at T would itself leak hindsight ('this was about to be
    revised')."""
    advance = _uap(
        "macro indicator: CPI",
        publication_time=AS_OF - timedelta(days=30),
        result=MacroObservation(indicator_name="CPI", value=2.9, unit="%"),
        vintage="advance estimate",
    )
    revision = _uap(
        "macro indicator: CPI",
        publication_time=AS_OF + timedelta(days=5),
        result=MacroObservation(indicator_name="CPI", value=3.1, unit="%"),
        vintage="second estimate",
    )
    revised_linked, advance_superseded_today = supersede(advance, revision)
    assert advance_superseded_today.validation_status == ValidationStatus.SUPERSEDED

    # Both the ORIGINAL (still VERIFIED) and the SUPERSEDED-marked copy
    # might plausibly be what a caller has on hand — feed the
    # SUPERSEDED-marked copy specifically, the harder case.
    snapshot = build_snapshot(AS_OF, [advance_superseded_today, revised_linked])

    assert len(snapshot.available_uaps) == 1
    selected = snapshot.available_uaps[0]
    assert selected.result.value == 2.9
    assert selected.validation_status == ValidationStatus.VERIFIED  # reconstructed, not today's SUPERSEDED


def test_revised_vintage_available_when_revision_predates_as_of():
    advance = _uap(
        "macro indicator: CPI",
        publication_time=AS_OF - timedelta(days=60),
        result=MacroObservation(indicator_name="CPI", value=2.9, unit="%"),
        vintage="advance estimate",
    )
    revised_linked, advance_superseded = supersede(
        advance,
        _uap(
            "macro indicator: CPI",
            publication_time=AS_OF - timedelta(days=10),  # revision ALSO predates as_of
            result=MacroObservation(indicator_name="CPI", value=3.1, unit="%"),
            vintage="second estimate",
        ),
    )
    snapshot = build_snapshot(AS_OF, [advance_superseded, revised_linked])

    assert len(snapshot.available_uaps) == 1
    selected = snapshot.available_uaps[0]
    assert selected.result.value == 3.1
    assert selected.vintage == "second estimate"
    assert advance_superseded.id in {u.id for u in snapshot.excluded_superseded_by_t}


def test_original_input_objects_are_never_mutated():
    advance = _uap(
        "macro indicator: CPI",
        publication_time=AS_OF - timedelta(days=30),
        result=MacroObservation(indicator_name="CPI", value=2.9, unit="%"),
    )
    revised_linked, advance_superseded_today = supersede(
        advance,
        _uap(
            "macro indicator: CPI",
            publication_time=AS_OF + timedelta(days=5),
            result=MacroObservation(indicator_name="CPI", value=3.1, unit="%"),
        ),
    )
    before = advance_superseded_today.model_dump()
    build_snapshot(AS_OF, [advance_superseded_today, revised_linked])
    after = advance_superseded_today.model_dump()
    assert before == after


# --- lookup helpers ---


def test_by_subject_returns_the_resolved_uap():
    uap = _uap("subject-a", publication_time=AS_OF - timedelta(days=1))
    snapshot = build_snapshot(AS_OF, [uap])
    assert snapshot.by_subject("subject-a").id == uap.id


def test_by_subject_returns_none_when_not_present():
    snapshot = build_snapshot(AS_OF, [])
    assert snapshot.by_subject("nonexistent") is None


def test_get_returns_uap_by_id():
    uap = _uap("subject-a", publication_time=AS_OF - timedelta(days=1))
    snapshot = build_snapshot(AS_OF, [uap])
    assert snapshot.get(uap.id).id == uap.id


def test_portfolio_and_mandate_are_carried_through():
    snapshot = build_snapshot(AS_OF, [], portfolio={"entity:a": 1.0}, mandate={"max_loss": 1000})
    assert snapshot.portfolio == {"entity:a": 1.0}
    assert snapshot.mandate == {"max_loss": 1000}
