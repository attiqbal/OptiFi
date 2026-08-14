def test_evidence_chain_resolves_a_real_uap(client):
    portfolio = client.get("/api/portfolio").json()
    holding_id = portfolio["holdings"][0]["fact"]["id"]
    r = client.get(f"/api/evidence/{holding_id}")
    assert r.status_code == 200
    j = r.json()
    assert j["root_id"] == holding_id
    assert j["chain"][0]["id"] == holding_id


def test_evidence_chain_reaches_multi_hop_dependencies(client):
    risk = client.get("/api/risk").json()
    scenario_uap_id = risk["scenario_sensitivity"]["entity:uk-gilts"]["id"]
    r = client.get(f"/api/evidence/{scenario_uap_id}")
    chain_ids = {u["id"] for u in r.json()["chain"]}
    assert scenario_uap_id in chain_ids
    assert len(chain_ids) > 1  # the causal claim + sensitivity feeding it are reachable too


def test_unknown_evidence_id_is_a_clean_404_not_a_fabricated_chain(client):
    r = client.get("/api/evidence/not-a-real-id")
    assert r.status_code == 404
