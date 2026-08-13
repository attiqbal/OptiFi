"""
Tests for the canonical asset identity layer (Phase E2).
"""

from optifi_data.asset_identity import AssetIdentity, asset_identity_conflicts, AssetType


def _equity(ticker="BP", exchange="LSE", currency="GBP", asset_type=AssetType.EQUITY, isin=None):
    return AssetIdentity(ticker=ticker, exchange=exchange, asset_type=asset_type, currency=currency, isin=isin)


def test_canonical_id_combines_exchange_and_ticker():
    identity = _equity()
    assert identity.canonical_id == "LSE:BP"


def test_same_ticker_different_exchange_is_not_the_same_asset():
    """Ticker strings alone are not globally unique — the core premise
    of this whole module."""
    lse_bp = _equity(ticker="BP", exchange="LSE")
    other_bp = _equity(ticker="BP", exchange="NYSE", currency="USD")
    assert lse_bp.same_asset_as(other_bp) is False
    assert lse_bp.canonical_id != other_bp.canonical_id


def test_identical_identities_are_the_same_asset():
    a = _equity()
    b = _equity()
    assert a.same_asset_as(b) is True


def test_same_ticker_and_exchange_but_different_asset_type_is_not_the_same_asset():
    equity = _equity(asset_type=AssetType.EQUITY)
    etf = _equity(asset_type=AssetType.ETF)
    assert equity.same_asset_as(etf) is False


# --- asset_identity_conflicts (required test category #8) ---


def test_no_conflict_for_genuinely_different_canonical_ids():
    a = _equity(ticker="BP", exchange="LSE")
    b = _equity(ticker="VOD", exchange="LSE")
    assert asset_identity_conflicts(a, b) == []


def test_no_conflict_for_identical_identities():
    a = _equity()
    b = _equity()
    assert asset_identity_conflicts(a, b) == []


def test_conflict_detected_for_shared_ticker_exchange_but_different_asset_type():
    a = _equity(asset_type=AssetType.EQUITY)
    b = _equity(asset_type=AssetType.ETF)
    conflicts = asset_identity_conflicts(a, b)
    assert len(conflicts) == 1
    assert "asset_type mismatch" in conflicts[0]


def test_conflict_detected_for_shared_ticker_exchange_but_different_currency():
    a = _equity(currency="GBP")
    b = _equity(currency="USD")
    conflicts = asset_identity_conflicts(a, b)
    assert any("currency mismatch" in c for c in conflicts)


def test_conflict_detected_for_mismatched_isin():
    a = _equity(isin="GB0007980591")
    b = _equity(isin="GB0000000000")
    conflicts = asset_identity_conflicts(a, b)
    assert any("isin mismatch" in c for c in conflicts)


def test_no_conflict_when_only_one_side_has_an_isin():
    """A missing isin on one side is not itself a conflict — only an
    actual mismatch between two KNOWN isins is."""
    a = _equity(isin="GB0007980591")
    b = _equity(isin=None)
    assert asset_identity_conflicts(a, b) == []


def test_multiple_simultaneous_conflicts_are_all_reported():
    a = _equity(asset_type=AssetType.EQUITY, currency="GBP")
    b = _equity(asset_type=AssetType.ETF, currency="USD")
    conflicts = asset_identity_conflicts(a, b)
    assert len(conflicts) == 2
