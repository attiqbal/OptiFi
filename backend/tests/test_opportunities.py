def test_default_variant_has_two_real_opportunities(client):
    r = client.get("/api/opportunities", params={"portfolio": "default"})
    j = r.json()
    kinds = {o["kind"] for o in j["opportunities"]}
    assert kinds == {"excess_idle_cash", "concentration"}
    assert j["no_opportunities_message"] is None


def test_no_opportunities_is_a_valid_real_state_never_padded(client):
    r = client.get("/api/opportunities", params={"portfolio": "efficient"})
    j = r.json()
    assert j["opportunities"] == []
    assert j["no_opportunities_message"] == (
        "No new opportunities today. Your capital allocation remains efficient "
        "against your current mandate."
    )


def test_opportunity_call_to_action_is_never_directive(client):
    r = client.get("/api/opportunities", params={"portfolio": "default"})
    for o in r.json()["opportunities"]:
        assert o["call_to_action"] in ("Review", "Analyse", "Compare", "Learn more")
