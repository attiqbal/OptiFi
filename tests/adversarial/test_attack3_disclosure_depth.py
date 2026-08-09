"""
Attack 3 — Disclosure Depth.

AI_ENGINE_SPEC.md Section 3.4 / Never-list item 9: "a non-VERIFIED item
reaching the user must say so." This attack builds a real multi-hop
chain — a PROVISIONAL fact feeding a causal claim, feeding a scenario
result, feeding a final "looks VERIFIED" judgement — then calls
explain_with_disclosure passing only the top-level judgement, NOT the
buried PROVISIONAL fact several hops upstream. Does the disclosure
requirement actually get enforced across the whole chain, or only
against whatever's directly handed to the function?

UPDATE (post-fix, round 1): explain_with_disclosure gained an optional
`known_uaps` lookup that, when provided, recursively walks
`dependencies`/`provenance_chain` to find every non-VERIFIED UAP at any
depth — see test_re_test_known_uaps_surfaces_the_buried_fact below,
using the exact same 4-hop scenario that originally found this gap.

UPDATE (post-fix, round 2): round 1 left a residual version of this same
gap — omitting `known_uaps` entirely silently fell back to the original
shallow behaviour, so a caller who forgot to pass it got exactly the
same silent, clean-looking disclosure Attack 3 originally found. That is
now closed too: an unresolved upstream reference always produces an
explicit "could not be checked" note, whether or not `known_uaps` was
supplied — see
test_no_known_uaps_at_all_now_produces_an_incompleteness_note_not_silence
below, using the exact same no-`known_uaps` call that originally
"passed" the exploit.
"""

from optifi_ai import StubExplanationGenerator, explain_with_disclosure
from optifi_causal import CausalClaim
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_simulation import ScenarioResult


def _build_four_hop_chain():
    # Hop 1: a genuinely uncorroborated, PROVISIONAL fact.
    provisional_fact = UAP(
        subject="Bank of England signalled a rate cut",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result="Bank of England signalled a rate cut",
        source="Illustrative Wire Service — not a real data source",
        producer="data-engine (test)",
        confidence=ConfidenceLevel.LOW,
    )

    # Hop 2: a causal claim resting on that fact.
    causal_claim = CausalClaim(
        subject="UK base rate cuts -> UK Gilts prices",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A reduction in the UK base rate is associated with higher UK Gilt prices",
        source="illustrative example — not a real data source",
        producer="causal-engine (test)",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id="entity:uk-base-rate",
        effect_entity_id="entity:uk-gilts",
        mechanism="Lower base rates reduce yields across the curve, pushing existing Gilt prices up.",
        dependencies=[provisional_fact.id],
    )

    # Hop 3: a scenario result resting on the causal claim.
    scenario_result = ScenarioResult(
        subject="illustrative scenario: UK base rate -100bp -> UK Gilts impact",
        validation_status=ValidationStatus.PROVISIONAL,
        result="UK Gilts estimated to appreciate under a 100bp base rate cut",
        source="illustrative example — not a real data source",
        producer="simulation-engine (test)",
        confidence=ConfidenceLevel.LOW,
        scenario_description="UK base rate: -100bp",
        affected_entity_id="entity:uk-gilts",
        base_case=0.028,
        range_low=-0.014,
        range_high=0.057,
        sensitivity_factors=["GBP response"],
        dependencies=[causal_claim.id],
    )

    # Hop 4: the "final" UAP a caller would hand to explain_with_disclosure
    # — deliberately marked VERIFIED at the surface, resting on a chain
    # that is genuinely PROVISIONAL two and three hops back.
    final_judgement = UAP(
        subject="portfolio impact judgement",
        information_class=InformationClass.JUDGEMENT,
        validation_status=ValidationStatus.VERIFIED,
        result="Increasing Gilt allocation appears favourable under the current rate outlook",
        source="ai-engine synthesis (test)",
        producer="ai-engine (test)",
        confidence=ConfidenceLevel.MODERATE,
        dependencies=[scenario_result.id],
    )

    return provisional_fact, causal_claim, scenario_result, final_judgement


def test_no_known_uaps_at_all_now_produces_an_incompleteness_note_not_silence():
    """
    RE-TEST, ROUND 2 (post-fix), using the exact same call that
    originally "passed" the exploit — only the top-level judgement,
    `known_uaps` not passed at all. This can no longer produce a clean,
    empty-looking disclosure: explain_with_disclosure now recognises
    final_judgement has an unresolved upstream reference and says so
    explicitly, rather than silently treating "nothing to check" and
    "couldn't check anything" as the same thing.
    """
    provisional_fact, causal_claim, scenario_result, final_judgement = _build_four_hop_chain()

    # The exact original exploit call: only the "final" thing, no
    # known_uaps at all.
    explanation = explain_with_disclosure([final_judgement], StubExplanationGenerator())

    assert explanation.limitations != []  # no longer silent
    joined = " ".join(explanation.limitations)
    assert "portfolio impact judgement" in joined  # names the UAP with the gap
    assert "could not be resolved" in joined
    assert scenario_result.id in joined  # names the specific unresolved reference

    # The chain genuinely IS traceable — this was never a case where the
    # information didn't exist, only that it wasn't checked.
    assert causal_claim.dependencies == [provisional_fact.id]
    assert scenario_result.dependencies == [causal_claim.id]
    assert final_judgement.dependencies == [scenario_result.id]


def test_re_test_known_uaps_surfaces_the_buried_fact():
    """
    RE-TEST (post-fix), using the exact same 4-hop scenario that
    originally found this gap: passing `known_uaps` now correctly walks
    the whole chain and discloses the buried PROVISIONAL fact, without
    the caller having to manually flatten it into the `uaps` argument
    themselves (contrast with test_control_passing_the_full_chain_
    explicitly_does_get_disclosed below, which required exactly that
    manual flattening before this fix existed).
    """
    provisional_fact, causal_claim, scenario_result, final_judgement = _build_four_hop_chain()
    known_uaps = {u.id: u for u in [provisional_fact, causal_claim, scenario_result, final_judgement]}

    # Only the top-level judgement is passed directly — exactly as in
    # the original exploit — but known_uaps now lets the function find
    # everything upstream of it too.
    explanation = explain_with_disclosure(
        [final_judgement], StubExplanationGenerator(), known_uaps=known_uaps
    )

    disclosure_text = " ".join(explanation.limitations)
    assert "Bank of England signalled a rate cut" in disclosure_text
    assert "PROVISIONAL" in disclosure_text
    # All three genuinely-PROVISIONAL upstream packets are caught — not
    # just the one directly passed in (which was VERIFIED and correctly
    # generates no note of its own).
    assert len(explanation.limitations) == 3


def test_control_passing_the_full_chain_explicitly_does_get_disclosed():
    """
    Control case: if a caller DOES pass every UAP in the chain directly
    (not relying on dependencies being walked), the PROVISIONAL fact is
    correctly flagged. This isolates the gap precisely: disclosure
    correctness is entirely dependent on caller discipline in what gets
    passed to `uaps`, not on any structural guarantee.
    """
    provisional_fact, causal_claim, scenario_result, final_judgement = _build_four_hop_chain()

    explanation = explain_with_disclosure(
        [provisional_fact, causal_claim, scenario_result, final_judgement],
        StubExplanationGenerator(),
    )

    disclosure_text = " ".join(explanation.limitations)
    assert "PROVISIONAL" in disclosure_text
    assert len(explanation.limitations) == 3  # fact, causal_claim, scenario_result — all PROVISIONAL
