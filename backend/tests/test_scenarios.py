def test_lists_all_seven_presets(client):
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert len(r.json()["scenarios"]) == 7


def test_rates_cut_scenario_is_runnable_and_never_implies_certainty(client):
    r = client.post("/api/scenarios/rates_cut_100bp/run")
    j = r.json()
    assert j["available"] is True
    dist = j["portfolio_distribution"]
    assert dist["range_low"] < dist["base_case"] < dist["range_high"]
    assert j["uncertainties"]


def test_unmodelled_scenario_is_unavailable_analysis_not_fabricated(client):
    r = client.post("/api/scenarios/fx_gbpusd_10pct_down/run")
    j = r.json()
    assert j["available"] is False
    assert "not yet modelled" in j["message"]
    assert "portfolio_distribution" not in j


def test_unknown_scenario_id_is_a_clean_404(client):
    r = client.post("/api/scenarios/not-a-real-scenario/run")
    assert r.status_code == 404
