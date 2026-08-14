"""
POST /api/ask — APP_UX_BLUEPRINT.md's "Ask OptiFi" screen, wrapping Phase
E6's `CIOOrchestrator.answer_query` directly rather than re-deriving
routing/roadblock/verification-gate/explanation logic here. A query
mentioning rebalancing deliberately routes through a real, over-tight
mandate (`_REJECT_TRIGGER_WORDS`) so a genuine `REJECT` verdict — and the
CIO's inability to override it — is a reachable, testable state, not
merely asserted in a unit test.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel

from optifi_ai.explanation import UserSophistication
from optifi_ai.generator import StubExplanationGenerator
from optifi_ai.intent import SpecialistEngine
from optifi_ai.orchestrator import CIOOrchestrator, SpecialistOutputPool, UserQuery
from optifi_optimisation import minimize_variance
from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_verification import verify_loss_cap_candidate

from ..demo_portfolio import RETURNS_BY_ENTITY, UK_BANK, UK_GILTS
from ..evidence_store import get_demo, serialize_uap

router = APIRouter(tags=["ask"])

_REJECT_TRIGGER_WORDS = ("rebalance", "reduce", "optimi")
_GENERATOR = StubExplanationGenerator()


def _competing_rate_forecasts(demo) -> list[UAP]:
    """Two genuinely different next-period UK-rate-path estimates, sharing
    a `disagreement_set_ref` — real, distinct numbers, not a single
    forecast duplicated. Lets 'conflicting models' be a reachable,
    testable Ask OptiFi state rather than only asserted in ai-engine's
    own unit tests."""
    common = dict(
        subject="UK base rate — 3-month-ahead path forecast",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        source="illustrative demo — two competing model families",
        confidence=ConfidenceLevel.LOW,
        disagreement_set_ref="uk-base-rate-3m-forecast",
        generated_at=demo.now,
    )
    return [
        UAP(**common, result=-0.25, producer="forecast-engine (illustrative econometric model)"),
        UAP(**common, result=0.10, producer="forecast-engine (illustrative ML model)"),
    ]


class AskRequest(BaseModel):
    text: str
    sophistication: str = "INFORMED"


def _build_pool(demo) -> SpecialistOutputPool:
    pool = SpecialistOutputPool()
    pool.add(SpecialistEngine.QUANT, [h.fact_uap for h in demo.holdings] + [demo.variance_uap, demo.parametric_var_uap])
    pool.add(SpecialistEngine.CAUSAL, demo.causal_claims)
    pool.add(SpecialistEngine.SIMULATION, list(demo.rate_cut_scenario_results.values()))
    pool.add(SpecialistEngine.FORECAST, _competing_rate_forecasts(demo))
    return pool


def _build_rejectable_candidate(demo):
    """A genuine REJECT, not a forced one: `minimize_variance` (no loss
    cap awareness) produces the minimum-variance candidate for the target
    return; `verify_loss_cap_candidate` then independently checks it
    against a stricter max_single_period_loss than the candidate was ever
    optimised for — a realistic mismatch (e.g. the mandate tightened
    after the candidate was generated), not an artificially infeasible
    solver call."""
    expected_returns = {e: sum(r) / len(r) for e, r in RETURNS_BY_ENTITY.items() if e in (UK_GILTS, UK_BANK)}
    covariance = {a: {b: demo.covariance_uap.result[a][b] for b in expected_returns} for a in expected_returns}
    target_return = sum(expected_returns.values()) / len(expected_returns)

    candidate = minimize_variance(
        expected_returns=expected_returns,
        covariance=covariance,
        target_return=target_return,
    )
    strict_max_loss = 500.0
    verdict = verify_loss_cap_candidate(
        weights=candidate.result["weights"],
        expected_returns=expected_returns,
        covariance=covariance,
        target_return=target_return,
        portfolio_value=demo.assets_total,
        max_single_period_loss=strict_max_loss,
        confidence_level=0.95,
        min_weight=0.0,
        max_weight=1.0,
    )
    return candidate, [verdict]


@router.post("/ask")
def ask(request: AskRequest, portfolio: str = Query("default", pattern="^(default|efficient)$")) -> dict:
    demo = get_demo(portfolio)
    pool = _build_pool(demo)

    try:
        sophistication = UserSophistication[request.sophistication.upper()]
    except KeyError:
        sophistication = UserSophistication.INFORMED

    candidate, verdicts = None, None
    if any(w in request.text.lower() for w in _REJECT_TRIGGER_WORDS):
        candidate, verdicts = _build_rejectable_candidate(demo)
        # The candidate genuinely was produced by optimisation-engine —
        # register it in the pool too, so roadblock reporting doesn't
        # claim OPTIMISATION produced nothing when a (subsequently
        # REJECTed) candidate demonstrably exists.
        pool.add(SpecialistEngine.OPTIMISATION, [candidate])

    orchestrator = CIOOrchestrator(_GENERATOR)
    routing, explanation = orchestrator.answer_query(
        UserQuery(request.text, sophistication=sophistication),
        pool,
        demo.now,
        timedelta(days=30),
        candidate=candidate,
        candidate_verdicts=verdicts,
    )

    return {
        "routing": {"engines": sorted(e.value for e in routing.engines), "reasoning": routing.reasoning},
        "facts": [serialize_uap(u) for u in explanation.facts],
        "estimates": [serialize_uap(u) for u in explanation.estimates],
        "judgements": [serialize_uap(u) for u in explanation.judgements],
        "disagreement_notes": explanation.disagreement_notes,
        "non_verified_disclosures": explanation.non_verified_disclosures,
        "roadblocks": [{"kind": r.kind, "description": r.description, "subject": r.subject} for r in explanation.roadblocks],
        "suggested_action": explanation.suggested_action,
        "why_ids": explanation.why_ids,
        "candidate": serialize_uap(candidate) if candidate is not None else None,
    }
