"""
Tests for SourceIdentity / same_source_identity (Phase E1 hardening).
"""

import pytest

from optifi_shared import same_source_identity, SourceIdentity


def test_same_publication_matches():
    a = SourceIdentity(publication="BBC News")
    b = SourceIdentity(publication="BBC News")
    assert same_source_identity(a, b) is True


def test_different_publications_no_further_structure_do_not_match():
    a = SourceIdentity(publication="BBC News")
    b = SourceIdentity(publication="The Guardian")
    assert same_source_identity(a, b) is False


def test_same_originating_document_id_matches_regardless_of_publication_names():
    """
    Test category #1 (required): same-origin news masquerading as
    independent sources — two clearly different-looking outlet names
    that both republish the SAME underlying wire story must be
    recognised as the same origin, via the shared originating_document_id,
    which is exactly the case a pure name heuristic could miss if the
    names shared no common substring.
    """
    a = SourceIdentity(publication="Financial Times", originating_document_id="wire-story-12345")
    b = SourceIdentity(publication="The Independent", originating_document_id="wire-story-12345")
    assert same_source_identity(a, b) is True


def test_different_originating_document_ids_do_not_match_even_with_similar_names():
    a = SourceIdentity(publication="BBC News", originating_document_id="wire-story-1")
    b = SourceIdentity(publication="BBC News", originating_document_id="wire-story-2")
    # Same publication, but the explicit document ids disagree —
    # explicit document identity is more authoritative than the name
    # heuristic and must not be overridden by it.
    assert same_source_identity(a, b) is False


def test_originator_takes_precedence_over_publication_name_mismatch():
    """
    Test category #2 (required): source aliases — two publications with
    completely different names, both carrying the SAME wire-service
    originator, are the same underlying origin even though their own
    publication names share no substring.
    """
    a = SourceIdentity(publication="Financial Times", originator="Reuters")
    b = SourceIdentity(publication="The Independent", originator="Reuters")
    assert same_source_identity(a, b) is True


def test_issuer_takes_precedence_over_originator_and_publication():
    a = SourceIdentity(publication="Outlet A", originator="Wire Service X", issuer="ONS")
    b = SourceIdentity(publication="Outlet B", originator="Wire Service Y", issuer="ONS")
    assert same_source_identity(a, b) is True


def test_shared_vendor_alone_does_not_imply_same_origin():
    """A shared data vendor is a pipe, not a source — two genuinely
    different, unrelated stories ingested through the same vendor must
    not be treated as the same origin."""
    a = SourceIdentity(publication="Outlet A", vendor="Bloomberg")
    b = SourceIdentity(publication="Outlet B", vendor="Bloomberg")
    assert same_source_identity(a, b) is False


def test_shared_redistributor_alone_does_not_imply_same_origin():
    a = SourceIdentity(publication="Outlet A", redistributor="Aggregator X")
    b = SourceIdentity(publication="Outlet B", redistributor="Aggregator X")
    assert same_source_identity(a, b) is False


def test_falls_back_to_bounded_substring_heuristic_on_publication_alone():
    a = SourceIdentity(publication="BBC")
    b = SourceIdentity(publication="BBC News")
    assert same_source_identity(a, b) is True


def test_publication_is_required():
    with pytest.raises(Exception):
        SourceIdentity()
