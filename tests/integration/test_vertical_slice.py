"""
End-to-end synthetic vertical slice — Phase 2C of the roadmap.

One illustrative portfolio, one controlled scenario ("UK base rate:
-100bp", the same scenario already used in causal-engine's and
simulation-engine's illustrative examples), wired through all seven
implemented engines using only functions that already exist, unmodified:

  data-engine        -> corroborate_fact
  forecast-engine     -> inverse_error_weighted_ensemble
  causal-engine       -> CausalClaim
  simulation-engine   -> ScenarioResult
  quant-engine        -> covariance_matrix, portfolio_variance, parametric_var
  optimisation-engine -> minimize_variance_with_loss_cap
  verification-engine -> verify_optimisation_candidate, verify_loss_cap_candidate,
                          check_provenance_resolvable
  ai-engine           -> group_by_disagreement_set, has_genuine_disagreement,
                          synthesize_with_disagreement_preserved, frame_candidate,
                          explain_with_disclosure

Every input is illustrative and clearly labeled as such, consistent with
every prior task in this project. No real data source or LLM provider is
used anywhere — StubExplanationGenerator is the only generator.

One point of remaining friction with the task's stated premise, resolved
without modifying any existing package (see the module-level comment at
the relevant construction site below for detail): causal-engine's only
existing illustrative example is a UK-base-rate -> mortgage-refinancing-
rate claim — no Gilts causal claim exists to "reuse" as originally
assumed. All three asset-specific CausalClaim instances (Gilts, Bank
Equities, Property) are constructed directly in this test, following
example_rate_cut_mortgage_claim's exact pattern, using only the
unmodified CausalClaim class.

Step 6 originally used `minimize_variance` (the uncapped solver) as a
workaround, since `minimize_variance_with_loss_cap` did not exist yet.
It now exists, with real loss-cap enforcement and optional
`covariance_source_id`/`expected_returns_source_id` parameters — Step 6
uses it directly, and `candidate.dependencies` now genuinely resolves
through to the covariance matrix UAP computed in Step 5, closing the
provenance gap the original vertical slice left open (see the Step 6
comment below for why `expected_returns_source_id` is deliberately left
unset).
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import t as student_t

from optifi_ai import (
    StubExplanationGenerator,
    explain_with_disclosure,
    frame_candidate,
    group_by_disagreement_set,
    has_genuine_disagreement,
    synthesize_with_disagreement_preserved,
)
from optifi_causal import CausalClaim
from optifi_data import corroborate_fact
from optifi_forecast import inverse_error_weighted_ensemble
from optifi_forecast.examples import EXAMPLE_HISTORICAL_ERRORS
from optifi_optimisation import minimize_variance_with_loss_cap
from optifi_quant import covariance_matrix, parametric_var, portfolio_variance
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_simulation import ScenarioResult
from optifi_simulation.examples import example_rate_cut_gilt_impact
from optifi_verification import (
    VerdictType,
    check_provenance_resolvable,
    verify_loss_cap_candidate,
    verify_optimisation_candidate,
)

# --- The illustrative mandate (kept consistent with earlier tasks, not arbitrary) ---
PORTFOLIO_VALUE = 500_000.0
CURRENT_WEIGHTS = {"UK_Gilts": 0.40, "UK_Bank_Equities": 0.30, "UK_Property": 0.30}
MAX_SINGLE_PERIOD_LOSS = 50_000.0
CONFIDENCE_LEVEL = 0.95
SCENARIO_DESCRIPTION = "UK base rate: -100bp"


# --- Step 5 helper: fresh SYNTHETIC returns, same documented pattern as ---
# --- quant-engine's tests/conftest.py (Student's t, fixed seed, 252 days) ---
# --- (that fixture lives in quant-engine's own test suite, not its ---
# --- installed package, so it isn't importable here — this reproduces ---
# --- the same formula rather than depending on another package's tests). ---
def _synthetic_daily_returns(
    seed: int, n_days: int, df: int, annual_mean: float, annual_vol: float
) -> list[float]:
    daily_mean = annual_mean / n_days
    daily_vol = annual_vol / (n_days**0.5)
    t_variance = df / (df - 2)
    scale = daily_vol / (t_variance**0.5)
    rng = np.random.default_rng(seed)
    raw_t_draws = student_t.rvs(df=df, size=n_days, random_state=rng)
    return (daily_mean + scale * raw_t_draws).tolist()


@pytest.fixture(scope="module")
def vertical_slice() -> dict:
    """
    Builds the entire chain once per test module and returns every
    intermediate UAP plus a registry (id -> UAP) for the evidence-chain
    traversal test.
    """
    registry: dict[str, UAP] = {}

    def _register(*uaps: UAP) -> None:
        for uap in uaps:
            registry[uap.id] = uap

    # === 1. data-engine: corroborate an illustrative PROVISIONAL fact ===
    provisional_fact = UAP(
        subject="Bank of England policy signal: openness to a 100bp cut",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result="Bank of England signalled openness to a 100bp base rate cut over the coming months",
        source="Illustrative Wire Service A — not a real data source",
        producer="data-engine (illustrative) / Stage 1-2 placeholder",
        confidence=ConfidenceLevel.LOW,
    )
    independent_source = UAP(
        subject="Bank of England policy signal: openness to a 100bp cut",
        information_class=InformationClass.FACT,
        validation_status=ValidationStatus.PROVISIONAL,
        result="Separately reports the Bank of England signalled openness to a 100bp base rate cut",
        source="Illustrative Wire Service B — not a real data source",
        producer="data-engine (illustrative) / Stage 1-2 placeholder",
        confidence=ConfidenceLevel.LOW,
    )
    verified_fact = corroborate_fact(provisional_fact, [independent_source])
    assert verified_fact.validation_status == ValidationStatus.VERIFIED
    _register(verified_fact, independent_source)

    # === 2. forecast-engine: three illustrative forecasts + ensemble ===
    forecast_subject = "illustrative: probability of a 100bp UK base rate cut within 6 months"
    disagreement_set_ref = "vertical-slice-100bp-cut-6m"
    forecasts = [
        UAP(
            subject=forecast_subject,
            information_class=InformationClass.ESTIMATE,
            validation_status=ValidationStatus.PROVISIONAL,
            result=0.35,
            source="illustrative example — not a real data source",
            producer="forecast-engine (illustrative) / econometric model",
            confidence=ConfidenceLevel.MODERATE,
            limitations=["illustrative only — not a real forecast"],
            dependencies=[verified_fact.id],
            disagreement_set_ref=disagreement_set_ref,
        ),
        UAP(
            subject=forecast_subject,
            information_class=InformationClass.ESTIMATE,
            validation_status=ValidationStatus.PROVISIONAL,
            result=0.55,
            source="illustrative example — not a real data source",
            producer="forecast-engine (illustrative) / ML model",
            confidence=ConfidenceLevel.MODERATE,
            limitations=["illustrative only — not a real forecast"],
            dependencies=[verified_fact.id],
            disagreement_set_ref=disagreement_set_ref,
        ),
        UAP(
            subject=forecast_subject,
            information_class=InformationClass.ESTIMATE,
            validation_status=ValidationStatus.PROVISIONAL,
            result=0.22,
            source="illustrative example — not a real data source",
            producer="forecast-engine (illustrative) / market-implied model",
            confidence=ConfidenceLevel.MODERATE,
            limitations=["illustrative only — not a real forecast"],
            dependencies=[verified_fact.id],
            disagreement_set_ref=disagreement_set_ref,
        ),
    ]
    _register(*forecasts)

    ensemble = inverse_error_weighted_ensemble(forecasts, EXAMPLE_HISTORICAL_ERRORS)
    _register(ensemble)

    # === 3. causal-engine: cause -> effect on all three assets ===
    # No existing Gilts causal claim exists to "reuse" (only the mortgage
    # example does) — see module docstring, friction point 2. All three
    # are constructed directly here, following example_rate_cut_mortgage_claim's
    # exact pattern (stated mechanism, LOW confidence, PROVISIONAL).
    causal_gilts = CausalClaim(
        subject="UK base rate cuts -> UK Gilts prices",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A reduction in the UK base rate is associated with higher UK Gilt prices",
        source="illustrative example — not a real data source",
        producer="causal-engine (illustrative) / CAUSAL_ENGINE_SPEC.md Section 5",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id="entity:uk-base-rate",
        effect_entity_id="entity:uk-gilts",
        mechanism=(
            "A lower base rate reduces yields across the curve; existing Gilts "
            "carrying higher fixed coupons become relatively more attractive, "
            "pushing their prices up, since bond prices move inversely to yields."
        ),
        limitations=["illustrative only — not derived from any real inference process, historical data, or model"],
    )
    causal_bank_equities = CausalClaim(
        subject="UK base rate cuts -> UK Bank Equities",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A reduction in the UK base rate is associated with pressure on UK bank equity valuations",
        source="illustrative example — not a real data source",
        producer="causal-engine (illustrative) / CAUSAL_ENGINE_SPEC.md Section 5",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id="entity:uk-base-rate",
        effect_entity_id="entity:uk-bank-equities",
        mechanism=(
            "Bank profitability depends heavily on net interest margin — the "
            "spread between what banks earn on loans and pay on deposits. A "
            "base rate cut compresses this spread, particularly where deposit "
            "rates are already low, pressuring bank equity valuations downward."
        ),
        limitations=["illustrative only — not derived from any real inference process, historical data, or model"],
    )
    causal_property = CausalClaim(
        subject="UK base rate cuts -> UK Property",
        validation_status=ValidationStatus.PROVISIONAL,
        result="A reduction in the UK base rate is associated with support for UK property valuations",
        source="illustrative example — not a real data source",
        producer="causal-engine (illustrative) / CAUSAL_ENGINE_SPEC.md Section 5",
        confidence=ConfidenceLevel.LOW,
        cause_entity_id="entity:uk-base-rate",
        effect_entity_id="entity:uk-property",
        mechanism=(
            "Lower base rates reduce mortgage and commercial borrowing costs, "
            "increasing effective demand for property and household/business "
            "capacity to service debt, which supports property valuations."
        ),
        limitations=["illustrative only — not derived from any real inference process, historical data, or model"],
    )
    causal_claims = [causal_gilts, causal_bank_equities, causal_property]
    _register(*causal_claims)

    # === 4. simulation-engine: extend the existing Gilts ScenarioResult ===
    # === to Bank Equities and Property, same scenario ===
    scenario_gilts = example_rate_cut_gilt_impact()
    scenario_bank_equities = ScenarioResult(
        subject="illustrative scenario: UK base rate -100bp -> UK Bank Equities impact",
        validation_status=ValidationStatus.PROVISIONAL,
        result="UK Bank Equities estimated to face modest valuation pressure under a 100bp base rate cut",
        source="illustrative example — not a real data source",
        producer="simulation-engine (illustrative) / SIMULATION_ENGINE_SPEC.md Section 7",
        confidence=ConfidenceLevel.LOW,
        scenario_description=SCENARIO_DESCRIPTION,
        affected_entity_id="entity:uk-bank-equities",
        base_case=-0.035,
        range_low=-0.07,
        range_high=0.01,
        sensitivity_factors=[
            "the extent to which banks can offset margin compression through "
            "fee income or cost-cutting",
            "whether the rate cut is accompanied by looser credit conditions "
            "that boost loan volumes, partially offsetting margin compression",
        ],
        limitations=["illustrative only — not derived from any real propagation process, historical data, or model"],
    )
    scenario_property = ScenarioResult(
        subject="illustrative scenario: UK base rate -100bp -> UK Property impact",
        validation_status=ValidationStatus.PROVISIONAL,
        result="UK Property estimated to appreciate modestly under a 100bp base rate cut",
        source="illustrative example — not a real data source",
        producer="simulation-engine (illustrative) / SIMULATION_ENGINE_SPEC.md Section 7",
        confidence=ConfidenceLevel.LOW,
        scenario_description=SCENARIO_DESCRIPTION,
        affected_entity_id="entity:uk-property",
        base_case=0.018,
        range_low=-0.01,
        range_high=0.045,
        sensitivity_factors=[
            "how much of the rate cut passes through to mortgage/commercial "
            "borrowing rates versus being absorbed by lender margins",
            "broader macroeconomic conditions (e.g. unemployment) that could "
            "offset the financing-cost benefit",
        ],
        limitations=["illustrative only — not derived from any real propagation process, historical data, or model"],
    )
    scenario_results = [scenario_gilts, scenario_bank_equities, scenario_property]
    _register(*scenario_results)

    # === 5. quant-engine: synthetic returns, covariance, current variance/VaR ===
    returns_by_asset = {
        "UK_Gilts": _synthetic_daily_returns(seed=101, n_days=252, df=4, annual_mean=0.03, annual_vol=0.06),
        "UK_Bank_Equities": _synthetic_daily_returns(seed=102, n_days=252, df=4, annual_mean=0.07, annual_vol=0.22),
        "UK_Property": _synthetic_daily_returns(seed=103, n_days=252, df=4, annual_mean=0.05, annual_vol=0.12),
    }
    cov_uap = covariance_matrix(returns_by_asset)
    covariance = cov_uap.result
    current_pv_uap = portfolio_variance(CURRENT_WEIGHTS, covariance)
    current_var_uap = parametric_var(
        portfolio_value=PORTFOLIO_VALUE,
        portfolio_std_dev=current_pv_uap.result**0.5,
        confidence_level=CONFIDENCE_LEVEL,
    )
    _register(cov_uap, current_pv_uap, current_var_uap)

    # === 6. optimisation-engine ===
    # Expected returns combine each asset's baseline synthetic annual mean
    # with the ScenarioResult's own base_case for this -100bp scenario —
    # the candidate is meant to reflect the portfolio re-optimised in
    # light of the scenario, not baseline history alone:
    #   Gilts:         0.03 (baseline) + 0.028 (scenario_gilts.base_case)  = 0.058
    #   Bank Equities: 0.07 (baseline) + (-0.06, in line with
    #                  scenario_bank_equities.base_case's direction)      = 0.010
    #   Property:      0.05 (baseline) + 0.015 (in line with
    #                  scenario_property.base_case's direction)           = 0.065
    expected_returns = {
        "UK_Gilts": 0.03 + scenario_gilts.base_case,
        "UK_Bank_Equities": 0.07 - 0.06,
        "UK_Property": 0.05 + 0.015,
    }
    # target_return=0.05 chosen via numeric prototyping (see task deliverable
    # #4): feasible within [min(expected_returns), max(expected_returns)],
    # and the resulting weights shift away from Bank Equities and towards
    # Gilts/Property — consistent with the causal/scenario story above —
    # while keeping the recomputed VaR comfortably under the $50,000 cap.
    target_return = 0.05
    # covariance_source_id: the real, resolvable link that was missing
    # before minimize_variance_with_loss_cap existed — cov_uap.id is a
    # genuine upstream UAP from Step 5, registered in the chain above.
    #
    # expected_returns_source_id: deliberately left unset. expected_returns
    # blends each asset's baseline synthetic annual mean with a scenario-
    # informed adjustment, but only UK_Gilts' adjustment is actually equal
    # to a real UAP field (scenario_gilts.base_case) — UK_Bank_Equities and
    # UK_Property use illustrative deltas "in line with" but not equal to
    # scenario_bank_equities.base_case / scenario_property.base_case (see
    # the comment above). There is no single UAP that cleanly represents
    # "the source of expected_returns" as a whole, so no id is supplied
    # here rather than inventing one that overstates the real provenance.
    candidate = minimize_variance_with_loss_cap(
        expected_returns,
        covariance,
        target_return,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=MAX_SINGLE_PERIOD_LOSS,
        confidence_level=CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
        covariance_source_id=cov_uap.id,
    )
    _register(candidate)

    # === 7. verification-engine ===
    weights = candidate.result["weights"]
    opt_verdict = verify_optimisation_candidate(
        weights, expected_returns, target_return, min_weight=0.0, max_weight=1.0
    )
    loss_cap_verdict = verify_loss_cap_candidate(
        weights,
        expected_returns,
        covariance,
        target_return,
        portfolio_value=PORTFOLIO_VALUE,
        max_single_period_loss=MAX_SINGLE_PERIOD_LOSS,
        confidence_level=CONFIDENCE_LEVEL,
        min_weight=0.0,
        max_weight=1.0,
    )
    provenance_verdict = check_provenance_resolvable(candidate, registry)

    # === 8. ai-engine ===
    groups = group_by_disagreement_set(forecasts)
    genuine_disagreement = has_genuine_disagreement(groups[disagreement_set_ref])
    cio_synthesis = synthesize_with_disagreement_preserved(groups, StubExplanationGenerator())
    _register(cio_synthesis)

    framed_candidate = frame_candidate(
        candidate,
        StubExplanationGenerator(),
        upstream_context=[*causal_claims, *scenario_results],
    )
    _register(framed_candidate)

    stage13_output = explain_with_disclosure([framed_candidate, cio_synthesis], StubExplanationGenerator())
    _register(stage13_output)

    return {
        "provisional_fact": provisional_fact,
        "independent_source": independent_source,
        "verified_fact": verified_fact,
        "forecasts": forecasts,
        "ensemble": ensemble,
        "disagreement_set_ref": disagreement_set_ref,
        "genuine_disagreement": genuine_disagreement,
        "causal_claims": causal_claims,
        "scenario_results": scenario_results,
        "returns_by_asset": returns_by_asset,
        "cov_uap": cov_uap,
        "current_pv_uap": current_pv_uap,
        "current_var_uap": current_var_uap,
        "expected_returns": expected_returns,
        "target_return": target_return,
        "candidate": candidate,
        "opt_verdict": opt_verdict,
        "loss_cap_verdict": loss_cap_verdict,
        "provenance_verdict": provenance_verdict,
        "cio_synthesis": cio_synthesis,
        "framed_candidate": framed_candidate,
        "stage13_output": stage13_output,
        "registry": registry,
    }


# === Step-by-step assertions ===


def test_step1_fact_is_independently_corroborated(vertical_slice):
    assert vertical_slice["verified_fact"].validation_status == ValidationStatus.VERIFIED
    assert vertical_slice["provisional_fact"].validation_status == ValidationStatus.PROVISIONAL


def test_step2_ensemble_computed_from_three_forecasts(vertical_slice):
    ensemble = vertical_slice["ensemble"]
    assert len(ensemble.dependencies) == 3
    assert ensemble.disagreement_set_ref == vertical_slice["disagreement_set_ref"]


def test_step3_causal_claims_cover_all_three_assets(vertical_slice):
    effect_ids = {c.effect_entity_id for c in vertical_slice["causal_claims"]}
    assert effect_ids == {"entity:uk-gilts", "entity:uk-bank-equities", "entity:uk-property"}
    for claim in vertical_slice["causal_claims"]:
        assert claim.information_class == InformationClass.ESTIMATE


def test_step4_scenario_results_cover_all_three_assets_with_expected_direction(vertical_slice):
    scenarios = {s.affected_entity_id: s for s in vertical_slice["scenario_results"]}
    assert scenarios["entity:uk-gilts"].base_case > 0
    assert scenarios["entity:uk-bank-equities"].base_case < 0
    assert scenarios["entity:uk-property"].base_case > 0


def test_step5_covariance_is_psd_and_var_is_positive(vertical_slice):
    # covariance_matrix() itself raises if not PSD (QUANT_ENGINE_SPEC.md
    # Section 9), so simply having reached this point is part of the proof.
    assert vertical_slice["current_var_uap"].result > 0


def test_step6_candidate_weights_sum_to_one_and_respect_bounds(vertical_slice):
    weights = vertical_slice["candidate"].result["weights"]
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)
    for w in weights.values():
        assert -1e-6 <= w <= 1.0 + 1e-6


def test_step6_candidate_now_references_the_real_covariance_source(vertical_slice):
    """
    Gap 2 fix (Commit 9ca118c) closed the loop this vertical slice
    originally left open: the candidate's dependencies/provenance_chain
    are no longer empty — they now genuinely resolve to the covariance
    matrix UAP computed in Step 5.
    """
    candidate = vertical_slice["candidate"]
    cov_uap = vertical_slice["cov_uap"]
    assert cov_uap.id in candidate.dependencies
    assert cov_uap.id in candidate.provenance_chain


def test_step6_loss_cap_is_independently_confirmed_within_mandate(vertical_slice):
    """
    Confirms the cap is genuinely satisfied in this pipeline — recomputed
    independently via quant-engine's own functions (mirroring what
    verify_loss_cap_candidate does internally), not merely trusted from
    the solver's self-reported figure or from the isolated unit tests.
    """
    candidate = vertical_slice["candidate"]
    cov_uap = vertical_slice["cov_uap"]
    weights = candidate.result["weights"]

    independently_recomputed_pv = portfolio_variance(weights, cov_uap.result)
    independently_recomputed_var = parametric_var(
        portfolio_value=PORTFOLIO_VALUE,
        portfolio_std_dev=independently_recomputed_pv.result**0.5,
        confidence_level=CONFIDENCE_LEVEL,
    ).result

    assert independently_recomputed_var <= MAX_SINGLE_PERIOD_LOSS
    assert independently_recomputed_var == pytest.approx(candidate.result["value_at_risk"], rel=1e-9)
    assert vertical_slice["loss_cap_verdict"].verdict_type == VerdictType.PASS


def test_step6_loss_cap_parameter_is_not_inert_for_this_scenarios_real_data(vertical_slice):
    """
    In this particular scenario the $50,000 cap turns out not to be the
    binding constraint (the natural minimum-variance portfolio at
    target_return=0.05 already sits well under it) — so this test proves
    the constraint is genuinely wired into the solver for THIS scenario's
    actual expected_returns/covariance, not merely present in the
    function signature: re-solving with the exact same inputs but an
    artificially tiny cap must reject, using this scenario's real numbers
    rather than a synthetic example from the unit tests.
    """
    with pytest.raises(ValueError, match="loss cap"):
        minimize_variance_with_loss_cap(
            vertical_slice["expected_returns"],
            vertical_slice["cov_uap"].result,
            vertical_slice["target_return"],
            portfolio_value=PORTFOLIO_VALUE,
            max_single_period_loss=1.0,  # artificially tiny — must bind
            confidence_level=CONFIDENCE_LEVEL,
            min_weight=0.0,
            max_weight=1.0,
        )


def test_step7_all_three_verification_checks_pass(vertical_slice):
    assert vertical_slice["opt_verdict"].verdict_type == VerdictType.PASS
    assert vertical_slice["loss_cap_verdict"].verdict_type == VerdictType.PASS
    # PASS WITH CAUTION, not a clean PASS: the candidate's provenance_chain
    # genuinely resolves and is acyclic, but references cov_uap
    # (quant-engine's covariance_matrix output), which is
    # validation_status=PROVISIONAL by design (quant-engine never marks
    # its own output VERIFIED) — VERIFICATION_FRAMEWORK.md Section 4's own
    # PASS WITH CAUTION example ("a dependency was itself only
    # PROVISIONAL") applies directly here, in this real pipeline, not
    # just in a synthetic unit-test scenario.
    assert vertical_slice["provenance_verdict"].verdict_type == VerdictType.PASS_WITH_CAUTION
    assert vertical_slice["cov_uap"].id in vertical_slice["provenance_verdict"].reasons[0]
    assert "PROVISIONAL" in vertical_slice["provenance_verdict"].reasons[0]


def test_step8_genuine_disagreement_preserved_across_all_three_forecasts(vertical_slice):
    assert vertical_slice["genuine_disagreement"] is True
    cio_synthesis = vertical_slice["cio_synthesis"]
    for forecast in vertical_slice["forecasts"]:
        assert forecast.id in cio_synthesis.dependencies
    assert len(cio_synthesis.dependencies) == 3


def test_step8_framed_candidate_figures_unaltered_and_references_upstream(vertical_slice):
    framed = vertical_slice["framed_candidate"]
    candidate = vertical_slice["candidate"]
    assert framed.result["original_figures"] == candidate.result
    for upstream in [*vertical_slice["causal_claims"], *vertical_slice["scenario_results"]]:
        assert upstream.id in framed.dependencies


def test_step8_stage13_output_discloses_non_verified_dependencies(vertical_slice):
    stage13_output = vertical_slice["stage13_output"]
    assert vertical_slice["framed_candidate"].id in stage13_output.dependencies
    assert vertical_slice["cio_synthesis"].id in stage13_output.dependencies

    joined = " ".join(stage13_output.limitations)
    # Both framed_candidate and cio_synthesis are PROVISIONAL, not
    # VERIFIED — the direct disclosure fires for both.
    assert stage13_output.limitations.count(
        f"Note: '{vertical_slice['framed_candidate'].subject}' has validation_status=PROVISIONAL, not VERIFIED."
    ) == 1
    assert stage13_output.limitations.count(
        f"Note: '{vertical_slice['cio_synthesis'].subject}' has validation_status=PROVISIONAL, not VERIFIED."
    ) == 1

    # This call site (Step 8, above) deliberately does not pass
    # known_uaps, even though the full registry exists — demonstrating
    # the fix this task adds on top of the earlier known_uaps opt-in:
    # explain_with_disclosure no longer produces a clean, empty-looking
    # disclosure just because a caller forgot to pass known_uaps. Both
    # framed_candidate and cio_synthesis have real upstream dependencies
    # (the optimisation candidate/causal claims/scenario results, and
    # the three forecasts, respectively) that go genuinely unresolved
    # here, and that incompleteness is now explicit rather than silent.
    assert "could not be resolved" in joined
    assert vertical_slice["candidate"].id in joined
    for forecast in vertical_slice["forecasts"]:
        assert forecast.id in joined
    assert len(stage13_output.limitations) == 4


# === Step 9: the evidence-chain traversal — the actual deliverable ===


def _walk_dependencies_and_provenance(start: UAP, registry: dict[str, UAP]) -> tuple[set[str], set[str]]:
    """
    Recursively walk `dependencies` and `provenance_chain` from `start`,
    resolving every referenced id against `registry`.

    Returns (reached, unresolved): `reached` is every packet id
    encountered (excluding start's own id); `unresolved` is any
    referenced id NOT found in `registry` — a broken link, which this
    function surfaces rather than silently skipping.
    """
    reached: set[str] = set()
    unresolved: set[str] = set()
    stack: list[str] = list(start.dependencies) + list(start.provenance_chain)

    while stack:
        current_id = stack.pop()
        if current_id in reached or current_id in unresolved:
            continue
        packet = registry.get(current_id)
        if packet is None:
            unresolved.add(current_id)
            continue
        reached.add(current_id)
        stack.extend(packet.dependencies)
        stack.extend(packet.provenance_chain)

    return reached, unresolved


def test_evidence_chain_from_stage13_output_reaches_fact_causal_claims_and_scenarios(vertical_slice):
    """
    The single most important assertion in this suite: starting from the
    final Stage 13 output, the evidence chain must reach all the way back
    to the original data-engine fact, all three causal claims, and all
    three scenario results — with no broken (unresolvable) link anywhere
    along the way.
    """
    stage13_output = vertical_slice["stage13_output"]
    registry = vertical_slice["registry"]

    reached, unresolved = _walk_dependencies_and_provenance(stage13_output, registry)

    assert not unresolved, f"evidence chain has unresolvable id(s): {unresolved}"

    assert vertical_slice["verified_fact"].id in reached, "chain does not reach the original data-engine fact"
    for claim in vertical_slice["causal_claims"]:
        assert claim.id in reached, f"chain does not reach causal claim: {claim.subject}"
    for scenario in vertical_slice["scenario_results"]:
        assert scenario.id in reached, f"chain does not reach scenario result: {scenario.subject}"

    # The new link (Gap 2 fix): candidate.dependencies is no longer
    # empty — it now resolves through to the real covariance matrix UAP
    # from Step 5, so the candidate is no longer a leaf node in this
    # traversal. Asserted at both ends: the direct edge exists on the
    # candidate itself, AND the recursive walk from the Stage 13 output
    # actually reaches it — proving the new link is walked, not just
    # present somewhere in the registry.
    cov_uap = vertical_slice["cov_uap"]
    assert cov_uap.id in vertical_slice["candidate"].dependencies, "candidate no longer references its covariance source"
    assert cov_uap.id in reached, "chain does not reach the covariance matrix UAP via the candidate"

    # Also confirm the intermediate hops that carry the chain are actually
    # present, not just its final targets — proves genuine multi-hop
    # traversal rather than every target being a direct dependency.
    assert vertical_slice["framed_candidate"].id in reached
    assert vertical_slice["cio_synthesis"].id in reached
    assert vertical_slice["candidate"].id in reached
    for forecast in vertical_slice["forecasts"]:
        assert forecast.id in reached
