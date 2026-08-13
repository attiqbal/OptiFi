"""
ModelRegistry — Part H: keeps every scorecard ever produced (an
append-only audit trail, never overwritten — same discipline as
`ForecastRecord`/`supersede()`) and answers the two questions
`forecast-engine`'s ensemble and confidence-calibration code need:
"what is this model's current standing" and "which models are currently
eligible to contribute to an ensemble for this target/horizon."
"""

from __future__ import annotations

from datetime import datetime, timezone

from .scorecard import DEFAULT_SCORECARD_STALENESS, determine_eligibility, Eligibility, ModelScorecard


def build_scorecard(
    model_id: str,
    model_version: str,
    target: str,
    horizon: str,
    training_window: tuple[datetime, datetime],
    evaluation_period: tuple[datetime, datetime],
    primary_metric_name: str,
    primary_metric_value: float,
    higher_is_better: bool,
    baseline_metric_value: float | None,
    n_evaluated: int,
    regimes_good: tuple[str, ...] = (),
    regimes_poor: tuple[str, ...] = (),
    last_evaluation: datetime | None = None,
    now: datetime | None = None,
) -> ModelScorecard:
    """Builds a scorecard with `eligibility` computed by
    `determine_eligibility` rather than left to the caller to set by
    hand — eligibility is always derived from the same figures the
    scorecard itself carries, never an independent claim."""
    last_evaluation = last_evaluation or datetime.now(timezone.utc)
    now = now or datetime.now(timezone.utc)
    eligibility = determine_eligibility(
        primary_metric_value=primary_metric_value,
        baseline_metric_value=baseline_metric_value,
        higher_is_better=higher_is_better,
        last_evaluation=last_evaluation,
        now=now,
    )
    return ModelScorecard(
        model_id=model_id,
        model_version=model_version,
        target=target,
        horizon=horizon,
        training_window=training_window,
        evaluation_period=evaluation_period,
        primary_metric_name=primary_metric_name,
        primary_metric_value=primary_metric_value,
        higher_is_better=higher_is_better,
        baseline_metric_value=baseline_metric_value,
        n_evaluated=n_evaluated,
        regimes_good=regimes_good,
        regimes_poor=regimes_poor,
        last_evaluation=last_evaluation,
        eligibility=eligibility,
    )


class ModelRegistry:
    """
    In-memory scorecard store. `register` is append-only — re-evaluating
    a model produces a NEW scorecard appended alongside the old one, the
    old one is never replaced in place (mirrors `ObservationCache`'s and
    `supersede()`'s "history is never overwritten" discipline elsewhere
    in this project).
    """

    def __init__(self) -> None:
        self._scorecards: list[ModelScorecard] = []

    def register(self, scorecard: ModelScorecard) -> None:
        self._scorecards.append(scorecard)

    def all_scorecards(self, model_id: str | None = None, target: str | None = None) -> list[ModelScorecard]:
        results = self._scorecards
        if model_id is not None:
            results = [s for s in results if s.model_id == model_id]
        if target is not None:
            results = [s for s in results if s.target == target]
        return list(results)

    def latest_scorecard(self, model_id: str, target: str, horizon: str) -> ModelScorecard | None:
        """Most recently evaluated scorecard for this exact
        model_id/target/horizon, or None if never evaluated. Ties in
        `last_evaluation` (e.g. a `refresh_staleness` copy of the same
        source) are broken by registration order — the later append
        wins, matching `eligible_scorecards`' own tie-break."""
        matches = [
            (idx, s)
            for idx, s in enumerate(self._scorecards)
            if s.model_id == model_id and s.target == target and s.horizon == horizon
        ]
        if not matches:
            return None
        _, best = max(matches, key=lambda pair: (pair[1].last_evaluation, pair[0]))
        return best

    def eligible_scorecards(self, target: str, horizon: str) -> list[ModelScorecard]:
        """The current, ELIGIBLE-only standing per model_id — the input
        set a performance-weighted ensemble should draw from (Part G /
        Part H: "a poor-performing model should be capable of losing
        weight or being retired"). Only the latest scorecard per
        model_id is considered; an old RETIRED scorecard being on record
        does not exclude a model that has since genuinely improved and
        re-earned ELIGIBLE via a fresh evaluation."""
        # Registration order is itself meaningful: `refresh_staleness`
        # appends a re-derived copy that shares its source's
        # `last_evaluation` (only the derived `eligibility` differs), so
        # `last_evaluation` alone cannot break a tie between an original
        # and its own refresh — the later list position must win.
        by_model: dict[str, tuple[int, ModelScorecard]] = {}
        for idx, s in enumerate(self._scorecards):
            if s.target != target or s.horizon != horizon:
                continue
            current = by_model.get(s.model_id)
            if current is None or (s.last_evaluation, idx) >= (current[1].last_evaluation, current[0]):
                by_model[s.model_id] = (idx, s)
        return [s for _, s in by_model.values() if s.eligibility == Eligibility.ELIGIBLE]

    def refresh_staleness(self, now: datetime | None = None) -> list[ModelScorecard]:
        """Re-derives eligibility for every registered scorecard against
        the current time (a scorecard that was ELIGIBLE when registered
        can become STALE purely by the passage of time, with no new
        evaluation) and appends fresh copies reflecting that — again,
        never mutates the originals. Returns the newly-appended
        scorecards."""
        now = now or datetime.now(timezone.utc)
        refreshed: list[ModelScorecard] = []
        for s in list(self._scorecards):
            new_eligibility = determine_eligibility(
                primary_metric_value=s.primary_metric_value,
                baseline_metric_value=s.baseline_metric_value,
                higher_is_better=s.higher_is_better,
                last_evaluation=s.last_evaluation,
                now=now,
            )
            if new_eligibility != s.eligibility:
                updated = build_scorecard(
                    model_id=s.model_id,
                    model_version=s.model_version,
                    target=s.target,
                    horizon=s.horizon,
                    training_window=s.training_window,
                    evaluation_period=s.evaluation_period,
                    primary_metric_name=s.primary_metric_name,
                    primary_metric_value=s.primary_metric_value,
                    higher_is_better=s.higher_is_better,
                    baseline_metric_value=s.baseline_metric_value,
                    n_evaluated=s.n_evaluated,
                    regimes_good=s.regimes_good,
                    regimes_poor=s.regimes_poor,
                    last_evaluation=s.last_evaluation,
                    now=now,
                )
                self._scorecards.append(updated)
                refreshed.append(updated)
        return refreshed
