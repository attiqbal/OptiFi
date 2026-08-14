def test_risk_smoke(client):
    r = client.get("/api/risk")
    assert r.status_code == 200
    j = r.json()
    assert "risk_contributors" in j
    assert "fx_exposure" in j
    assert "duration" in j


def test_risk_contributions_sum_to_one(client):
    r = client.get("/api/risk")
    contributions = r.json()["risk_contributors"]["result"]
    assert abs(sum(contributions.values()) - 1.0) < 1e-6


def test_fx_exposure_excludes_gbp(client):
    r = client.get("/api/risk")
    assert "GBP" not in r.json()["fx_exposure"]
    assert "USD" in r.json()["fx_exposure"]
    assert "EUR" in r.json()["fx_exposure"]


def test_scenario_sensitivity_covers_rate_sensitive_holdings(client):
    r = client.get("/api/risk")
    assert set(r.json()["scenario_sensitivity"].keys()) == {"entity:uk-gilts", "entity:uk-bank-equity"}
