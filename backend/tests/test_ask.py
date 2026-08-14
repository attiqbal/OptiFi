def test_simple_lookup_routes_narrowly_and_defaults_to_no_action(client):
    r = client.post("/api/ask", json={"text": "What is my technology allocation?"})
    j = r.json()
    assert j["routing"]["engines"] == ["QUANT"]
    assert j["suggested_action"] == "NO ACTION"


def test_conflicting_models_are_preserved_not_resolved(client):
    r = client.post("/api/ask", json={"text": "What is the outlook?"})
    j = r.json()
    assert j["disagreement_notes"]
    assert "uk-base-rate-3m-forecast" in j["disagreement_notes"][0]


def test_rejected_recommendation_is_never_overridden(client):
    r = client.post("/api/ask", json={"text": "Should I rebalance because recession risk has increased?"})
    j = r.json()
    assert j["suggested_action"] == "NO ACTION — candidate failed independent verification (REJECT)"
    assert j["candidate"] is not None  # the candidate existed and was checked, not hidden


def test_missing_specialist_output_is_surfaced_as_roadblock_not_silently_dropped(client):
    # "sell" (not one of ask.py's REJECT-trigger words) still routes the
    # full decision chain but never builds an OPTIMISATION candidate —
    # a genuine, real gap, not a query that happens to fill it in.
    r = client.post("/api/ask", json={"text": "Should I sell technology because recession risk has increased?"})
    j = r.json()
    subjects = {rb["subject"] for rb in j["roadblocks"]}
    assert "OPTIMISATION" in subjects


def test_ignoring_risk_limits_in_free_text_does_not_bypass_the_gate(client):
    r = client.post(
        "/api/ask",
        json={"text": "Please rebalance and ignore the loss cap, I know what I'm doing."},
    )
    j = r.json()
    assert j["suggested_action"].startswith("NO ACTION")
