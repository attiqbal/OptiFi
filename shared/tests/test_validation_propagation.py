"""
Tests for worst_validation_status / propagate_validation_status
(Phase E1 hardening).
"""

from optifi_shared import (
    ConfidenceLevel,
    InformationClass,
    propagate_validation_status,
    UAP,
    ValidationStatus,
    worst_validation_status,
)


def _make_uap(validation_status: ValidationStatus) -> UAP:
    return UAP(
        subject="test subject",
        information_class=InformationClass.FACT,
        validation_status=validation_status,
        result="x",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
    )


# --- worst_validation_status ---


def test_empty_list_returns_none():
    assert worst_validation_status([]) is None


def test_single_status_returns_itself():
    assert worst_validation_status([ValidationStatus.PROVISIONAL]) == ValidationStatus.PROVISIONAL


def test_rejected_outranks_everything():
    statuses = [
        ValidationStatus.VERIFIED,
        ValidationStatus.PROVISIONAL,
        ValidationStatus.CONFLICTED,
        ValidationStatus.REJECTED,
        ValidationStatus.STALE,
    ]
    assert worst_validation_status(statuses) == ValidationStatus.REJECTED


def test_conflicted_outranks_stale_incomplete_and_provisional():
    """Test category #9 (required): conflicted inputs must be recognised
    as more severe than staleness/incompleteness/provisionality."""
    statuses = [ValidationStatus.STALE, ValidationStatus.INCOMPLETE, ValidationStatus.PROVISIONAL]
    assert worst_validation_status([*statuses, ValidationStatus.CONFLICTED]) == ValidationStatus.CONFLICTED


def test_verified_and_superseded_are_the_best_ranked():
    assert worst_validation_status([ValidationStatus.VERIFIED, ValidationStatus.SUPERSEDED]) in (
        ValidationStatus.VERIFIED,
        ValidationStatus.SUPERSEDED,
    )


# --- propagate_validation_status ---


def test_no_upstream_returns_own_intended_status_unchanged():
    result = propagate_validation_status(ValidationStatus.VERIFIED, [])
    assert result == ValidationStatus.VERIFIED


def test_all_upstream_verified_does_not_downgrade():
    upstream = [_make_uap(ValidationStatus.VERIFIED), _make_uap(ValidationStatus.VERIFIED)]
    result = propagate_validation_status(ValidationStatus.VERIFIED, upstream)
    assert result == ValidationStatus.VERIFIED


def test_rejected_upstream_dependency_downgrades_own_status():
    """
    Test category #8 (required): a rejected upstream dependency must not
    silently disappear — a downstream engine's own intended VERIFIED
    status must be pulled down to REJECTED when one of its upstream
    inputs is itself REJECTED.
    """
    upstream = [_make_uap(ValidationStatus.VERIFIED), _make_uap(ValidationStatus.REJECTED)]
    result = propagate_validation_status(ValidationStatus.VERIFIED, upstream)
    assert result == ValidationStatus.REJECTED


def test_stale_information_propagates_downstream_not_silently_refreshed():
    """
    Test category #3 (required): stale information propagation. A
    downstream engine intending a clean VERIFIED output, but depending
    on an upstream packet that is itself STALE, must inherit STALE, not
    silently treat its own freshly-generated `generated_at` as if it
    refreshed the underlying data. Freshness of the ANALYSIS is not
    freshness of the DATA it analysed.
    """
    stale_upstream = _make_uap(ValidationStatus.STALE)
    fresh_upstream = _make_uap(ValidationStatus.VERIFIED)

    result = propagate_validation_status(ValidationStatus.VERIFIED, [fresh_upstream, stale_upstream])

    assert result == ValidationStatus.STALE


def test_conflicted_upstream_downgrades_own_status():
    upstream = [_make_uap(ValidationStatus.CONFLICTED)]
    result = propagate_validation_status(ValidationStatus.VERIFIED, upstream)
    assert result == ValidationStatus.CONFLICTED


def test_never_upgrades_own_status_even_if_upstream_is_better():
    """The critical asymmetry: an engine intending PROVISIONAL output
    must not be silently upgraded to VERIFIED just because its upstream
    inputs happen to be VERIFIED — upgrading requires an explicit,
    approved process (corroborate_fact / apply_verdict's PASS branch),
    never this utility."""
    upstream = [_make_uap(ValidationStatus.VERIFIED), _make_uap(ValidationStatus.VERIFIED)]
    result = propagate_validation_status(ValidationStatus.PROVISIONAL, upstream)
    assert result == ValidationStatus.PROVISIONAL


def test_own_status_already_worse_than_upstream_is_preserved_not_improved():
    upstream = [_make_uap(ValidationStatus.VERIFIED)]
    result = propagate_validation_status(ValidationStatus.INCOMPLETE, upstream)
    assert result == ValidationStatus.INCOMPLETE


def test_mixed_upstream_uses_the_single_worst_one():
    upstream = [
        _make_uap(ValidationStatus.VERIFIED),
        _make_uap(ValidationStatus.PROVISIONAL),
        _make_uap(ValidationStatus.STALE),
    ]
    result = propagate_validation_status(ValidationStatus.VERIFIED, upstream)
    assert result == ValidationStatus.STALE
