"""
Independent check on ai-engine's Stage 10 candidate framing —
VERIFICATION_FRAMEWORK.md Section 6: confirm framing hasn't altered the
figures optimisation-engine produced, rather than trusting frame_candidate's
own structural guarantee that it didn't.

Does not import optifi_ai or call frame_candidate or any of its internal
logic — this compares two already-existing UAPs directly, so it catches a
regression even if a future change to ai-engine broke that guarantee.
"""

from __future__ import annotations

from optifi_shared import UAP

from .verdict import FailureCategory, Verdict, VerdictType


def verify_candidate_framing_unaltered(original_candidate: UAP, framed_output: UAP) -> Verdict:
    """
    `frame_candidate`'s current output shape is
    `result = {"narrative": ..., "original_figures": ...}`. This function
    reads that shape rather than assuming it, and rejects — instead of
    crashing — if `framed_output.result` doesn't actually look like that.
    """
    if not isinstance(framed_output.result, dict) or "original_figures" not in framed_output.result:
        return Verdict(
            verdict_type=VerdictType.REJECT,
            reasons=[
                "framed_output.result does not contain a usable "
                f"'original_figures' structure (got: {framed_output.result!r})"
            ],
            failure_category=FailureCategory.DATA_QUALITY,
        )

    real_figures = original_candidate.result
    claimed_figures = framed_output.result["original_figures"]

    if claimed_figures == real_figures:
        return Verdict(
            verdict_type=VerdictType.PASS,
            reasons=["framed_output's original_figures exactly matches original_candidate.result"],
        )

    return Verdict(
        verdict_type=VerdictType.REJECT,
        reasons=[_describe_figure_discrepancy(real_figures, claimed_figures)],
        failure_category=FailureCategory.DATA_QUALITY,
    )


def _describe_figure_discrepancy(real_figures: object, claimed_figures: object) -> str:
    if isinstance(real_figures, dict) and isinstance(claimed_figures, dict):
        differences = []
        for key in sorted(set(real_figures) | set(claimed_figures)):
            real_value = real_figures.get(key, "<missing>")
            claimed_value = claimed_figures.get(key, "<missing>")
            if real_value != claimed_value:
                differences.append(f"'{key}': candidate={real_value!r} vs framed={claimed_value!r}")
        return "framed figures differ from original_candidate.result: " + "; ".join(differences)

    return (
        "framed figures differ from original_candidate.result: "
        f"candidate={real_figures!r} vs framed={claimed_figures!r}"
    )
