from optifi_ai.intent import classify_required_engines, SpecialistEngine


def test_simple_lookup_routes_quant_only():
    decision = classify_required_engines("What is my technology allocation?")
    assert decision.engines == frozenset({SpecialistEngine.QUANT})
    assert decision.reasoning


def test_complex_decision_routes_full_chain():
    decision = classify_required_engines("Should I reduce equities because recession risk has increased?")
    assert decision.engines == frozenset(
        {
            SpecialistEngine.CAUSAL,
            SpecialistEngine.FORECAST,
            SpecialistEngine.SIMULATION,
            SpecialistEngine.QUANT,
            SpecialistEngine.OPTIMISATION,
            SpecialistEngine.VERIFICATION,
        }
    )


def test_optimisation_always_pulls_in_verification():
    decision = classify_required_engines("should i rebalance")
    assert SpecialistEngine.OPTIMISATION in decision.engines
    assert SpecialistEngine.VERIFICATION in decision.engines


def test_unrecognised_query_defaults_to_quant_not_everything():
    decision = classify_required_engines("asdkjaslkdjalksjd")
    assert decision.engines == frozenset({SpecialistEngine.QUANT})


def test_routing_decision_is_a_heuristic_not_real_nlu():
    decision = classify_required_engines("What is my technology allocation?")
    assert decision.is_heuristic is True
