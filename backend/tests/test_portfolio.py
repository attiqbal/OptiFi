def test_portfolio_smoke(client):
    r = client.get("/api/portfolio")
    assert r.status_code == 200
    j = r.json()
    assert j["assets_total"] == 548_600.0
    assert j["liabilities_total"] == 120_000.0
    assert j["net_capital"] == 428_600.0
    assert len(j["holdings"]) == 5


def test_holdings_are_fact_class_and_verified(client):
    r = client.get("/api/portfolio")
    for h in r.json()["holdings"]:
        assert h["fact"]["information_class"] == "FACT"
        assert h["fact"]["validation_status"] == "VERIFIED"


def test_risk_figures_are_estimate_class_not_fact(client):
    r = client.get("/api/portfolio")
    risk = r.json()["risk"]
    assert risk["portfolio_variance"]["information_class"] == "ESTIMATE"
    assert risk["parametric_var_95"]["information_class"] == "ESTIMATE"


def test_allocation_weights_sum_to_one(client):
    r = client.get("/api/portfolio")
    total = sum(r.json()["allocation"].values())
    assert abs(total - 1.0) < 1e-6


def test_stale_data_is_surfaced_against_present_time(client):
    r = client.get("/api/portfolio")
    freshness = r.json()["data_freshness"]
    assert freshness["checked_against_present_time"] is True
    assert len(freshness["stale_items"]) == 1
    assert freshness["stale_items"][0]["kind"] == "STALE_DATA"


def test_default_variant_breaches_technology_concentration_target(client):
    r = client.get("/api/portfolio", params={"portfolio": "default"})
    assert r.json()["concentration"]["technology_breach"] is True


def test_efficient_variant_does_not_breach_technology_concentration_target(client):
    r = client.get("/api/portfolio", params={"portfolio": "efficient"})
    assert r.json()["concentration"]["technology_breach"] is False
