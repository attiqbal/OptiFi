def test_covered_asset_smoke(client):
    r = client.get("/api/research/entity:uk-gilts")
    assert r.status_code == 200
    j = r.json()
    assert j["covered"] is True
    assert j["forecasts"][0]["information_class"] == "ESTIMATE"
    assert "entity:uk-gilts" in j["scenarios"]


def test_unavailable_analysis_for_an_unsupported_asset_is_never_fabricated(client):
    r = client.get("/api/research/entity:unknown-crypto")
    assert r.status_code == 200
    j = r.json()
    assert j["covered"] is False
    assert "message" in j
    assert "forecasts" not in j


def test_asset_plus_you_shows_current_and_hypothetical_exposure(client):
    r = client.get("/api/research/entity:us-tech-equity")
    plus_you = r.json()["asset_plus_you"]
    assert plus_you["current_portfolio_exposure"] > 0
    assert plus_you["if_10000_invested"]["exposure_after"] > plus_you["current_portfolio_exposure"]


def test_asset_with_no_causal_coverage_returns_empty_not_fabricated(client):
    r = client.get("/api/research/entity:cash-gbp")
    j = r.json()
    assert j["covered"] is True
    assert j["causal_exposures"] == []
    assert j["scenarios"] == {}
