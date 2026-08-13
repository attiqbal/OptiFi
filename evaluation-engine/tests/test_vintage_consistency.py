"""
Testing Requirement: "revised macro data" — a forecast whose input
vintage has since been revised must be flagged, not silently re-scored
as if nothing changed.
"""

from optifi_evaluation import check_vintage_consistency


def test_matching_vintage_is_current():
    result = check_vintage_consistency("second estimate", "second estimate")
    assert result.status == "CURRENT"


def test_revised_vintage_is_flagged_stale_vintage():
    result = check_vintage_consistency("advance estimate", "second estimate")
    assert result.status == "STALE_VINTAGE"
    assert "advance estimate" in result.message
    assert "second estimate" in result.message


def test_missing_vintage_info_is_unverifiable_not_silently_current():
    result = check_vintage_consistency(None, "second estimate")
    assert result.status == "UNVERIFIABLE"
