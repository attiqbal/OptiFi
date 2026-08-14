"""
SensitivityRegistry — PHASE E4 brief, Part 4 ("Regime Awareness"):
"Relationships may change across [regimes]... Do not assume fixed
coefficients always apply. Start simple but design for regime
conditioning."

This registry stores sensitivity UAPs (from `factor_sensitivity.py`,
statistical or deterministic) keyed by `(factor_id, asset_id, regime)`
and answers "what's the best available sensitivity for this factor/asset
pair, under this regime?" with an EXPLICIT, inspectable fallback signal —
never a silent substitution of a regime-agnostic estimate for a
regime-specific one the caller actually asked for.

Deliberately NOT included: any mechanism to classify which regime the
market or economy is *currently* in from raw data. Regime DETECTION is a
substantially different, genuinely unresolved research question (what
axes matter — inflation level, credit cycle, volatility regime; how are
thresholds defined; is it a hard classification or a continuous/fuzzy
one) — this project does not silently invent an answer to it here (see
the Phase E4 deliverable's "unresolved research questions"). This
registry only conditions on a `regime` LABEL the caller already has in
hand — where that label comes from is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from optifi_shared import ConflictedInputFailure, MissingInputFailure, OutOfDistributionFailure, UAP


@dataclass(frozen=True)
class SensitivityLookupResult:
    """
    `matches`: every currently-registered sensitivity UAP satisfying the
    lookup — plural when competing estimates disagree (Testing
    Requirement "conflicting asset-response models"), preserved rather
    than silently reconciled into one, per this project's existing
    multi-model-disagreement discipline.
    `regime_matched`: True if `matches` were estimated specifically under
    the requested regime; False if they are the regime-agnostic fallback.
    `fallback_used`: True whenever `regime_matched` is False but a
    result was still returned — makes the substitution visible to the
    caller rather than indistinguishable from a genuine regime-specific
    hit.
    """

    matches: tuple[UAP, ...]
    regime_matched: bool
    fallback_used: bool

    def single(self) -> UAP:
        """Convenience for a caller that specifically wants exactly one
        sensitivity and considers more than one an error requiring
        explicit resolution — raises `ConflictedInputFailure` rather
        than silently picking the first match."""
        if len(self.matches) > 1:
            raise ConflictedInputFailure(
                f"SensitivityLookupResult.single(): {len(self.matches)} competing "
                "sensitivity estimates are registered for this factor/asset/regime "
                "combination — this caller has no basis to silently pick one; "
                "resolve the disagreement explicitly (e.g. present both, or "
                "combine via an explicit, documented method) rather than calling "
                "single()."
            )
        return self.matches[0]


class SensitivityRegistry:
    """In-memory store of sensitivity UAPs, keyed by
    `(factor_id, asset_id)` and further partitioned by the `regime` each
    entry's own `result["regime"]` states (`None` = regime-agnostic)."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], list[UAP]] = {}

    def register(self, factor_id: str, asset_id: str, sensitivity_uap: UAP) -> None:
        self._entries.setdefault((factor_id, asset_id), []).append(sensitivity_uap)

    def get_sensitivity(
        self, factor_id: str, asset_id: str, regime: str | None = None, allow_fallback: bool = True
    ) -> SensitivityLookupResult:
        """
        Two distinct, deliberately different failure modes:

        - Testing Requirement "missing factor exposure": if NOTHING has
          ever been registered for `(factor_id, asset_id)` — no
          sensitivity has been estimated for this pathway under ANY
          regime — raises `MissingInputFailure`. This is a structural
          gap (the pathway may be causally supported, but nothing
          quantifies it), not a regime-conditioning problem.
        - Testing Requirement "regime mismatch": if entries DO exist for
          this factor/asset pair, just not for the requested regime (and
          no permitted fallback), raises `OutOfDistributionFailure` —
          the pathway is quantified, just not under the conditions
          asked for.

        Fallback only ever goes from regime-specific request ->
        regime-agnostic entry, never the reverse (a caller explicitly
        asking for the regime-agnostic estimate, `regime=None`, does not
        get silently handed a regime-specific one — that would
        understate how conditional the estimate actually is).
        """
        all_entries = self._entries.get((factor_id, asset_id), [])
        if not all_entries:
            raise MissingInputFailure(
                f"SensitivityRegistry.get_sensitivity: no sensitivity has ever "
                f"been estimated for ({factor_id!r}, {asset_id!r}) under any "
                "regime — this pathway may be causally supported, but nothing "
                "quantifies it yet (missing factor exposure)."
            )

        exact = tuple(e for e in all_entries if e.result.get("regime") == regime)
        if exact:
            return SensitivityLookupResult(matches=exact, regime_matched=True, fallback_used=False)

        if regime is not None and allow_fallback:
            regime_agnostic = tuple(e for e in all_entries if e.result.get("regime") is None)
            if regime_agnostic:
                return SensitivityLookupResult(matches=regime_agnostic, regime_matched=False, fallback_used=True)

        raise OutOfDistributionFailure(
            f"SensitivityRegistry.get_sensitivity: sensitivity estimates exist "
            f"for ({factor_id!r}, {asset_id!r}), but none under regime "
            f"{regime!r}"
            + ("" if not allow_fallback else ", and no regime-agnostic fallback is registered either")
            + " — this project never fabricates a regime-specific figure that "
            "hasn't actually been estimated under that regime."
        )
