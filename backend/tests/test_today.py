def test_today_smoke(client):
    r = client.get("/api/today")
    assert r.status_code == 200
    j = r.json()
    assert j["portfolio_value"]["information_class"] == "FACT"
    assert j["portfolio_value"]["validation_status"] == "VERIFIED"
    assert len(j["developments"]) >= 1


def test_default_variant_has_three_developments():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).get("/api/today", params={"portfolio": "default"})
    assert len(r.json()["developments"]) == 3


def test_efficient_variant_never_pads_developments_to_a_fixed_count(client):
    r = client.get("/api/today", params={"portfolio": "efficient"})
    developments = r.json()["developments"]
    # The efficient variant has no concentration/idle-cash breach — only
    # the rate-change development should be real, not padded to 3.
    assert len(developments) == 1


def test_capital_efficiency_never_flagged_authoritative_while_provisional(client):
    r = client.get("/api/today")
    ces = r.json()["capital_efficiency"]
    assert ces["validation_status"] == "PROVISIONAL"
    assert ces["authoritative"] is False


def test_rate_development_never_uses_directive_language(client):
    r = client.get("/api/today")
    for d in r.json()["developments"]:
        assert d["suggested_action"] in ("NO ACTION", "MONITOR", "REVIEW", "ANALYSE", "COMPARE")
