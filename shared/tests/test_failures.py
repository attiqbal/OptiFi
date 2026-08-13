"""
Tests for the structured analytical-failure hierarchy (Phase E1
hardening).
"""

import pytest

from optifi_shared import (
    AnalyticalFailure,
    ConflictedInputFailure,
    InsufficientDataFailure,
    MissingInputFailure,
    ModelFailure,
    OutOfDistributionFailure,
    StaleInputFailure,
    UnsupportedFailure,
    VerificationFailure,
)

ALL_FAILURE_TYPES = [
    MissingInputFailure,
    StaleInputFailure,
    ConflictedInputFailure,
    InsufficientDataFailure,
    UnsupportedFailure,
    OutOfDistributionFailure,
    ModelFailure,
    VerificationFailure,
]


@pytest.mark.parametrize("failure_type", ALL_FAILURE_TYPES)
def test_every_failure_type_is_a_value_error(failure_type):
    """Backward compatibility, the whole point of this design: every
    existing `pytest.raises(ValueError)` anywhere in the codebase must
    continue to match, whether or not a raise site has migrated to one
    of these specific categories."""
    with pytest.raises(ValueError):
        raise failure_type("illustrative failure")


@pytest.mark.parametrize("failure_type", ALL_FAILURE_TYPES)
def test_every_failure_type_is_an_analytical_failure(failure_type):
    with pytest.raises(AnalyticalFailure):
        raise failure_type("illustrative failure")


def test_each_failure_type_has_a_distinct_machine_readable_category():
    categories = {failure_type.category for failure_type in ALL_FAILURE_TYPES}
    assert categories == {
        "MISSING_INPUT",
        "STALE_INPUT",
        "CONFLICTED_INPUT",
        "INSUFFICIENT_DATA",
        "UNSUPPORTED",
        "OUT_OF_DISTRIBUTION",
        "MODEL_FAILURE",
        "VERIFICATION_FAILURE",
    }


def test_caller_can_branch_on_specific_category_not_just_message_parsing():
    def _raises_missing_input():
        raise MissingInputFailure("expected_returns was not supplied")

    try:
        _raises_missing_input()
        assert False, "should have raised"
    except MissingInputFailure as exc:
        assert exc.category == "MISSING_INPUT"
    except AnalyticalFailure:
        assert False, "should have been caught by the more specific except clause above"


def test_a_specific_category_does_not_falsely_match_a_different_category():
    with pytest.raises(MissingInputFailure):
        raise MissingInputFailure("x")

    with pytest.raises(AnalyticalFailure):
        with pytest.raises(MissingInputFailure):
            raise StaleInputFailure("x")  # a different category — must NOT be caught as MissingInputFailure
