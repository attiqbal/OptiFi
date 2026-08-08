"""
The verdict taxonomy — VERIFICATION_FRAMEWORK.md, Section 4 (verdict
types) and Section 5.7 (failure classification).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from optifi_shared import ValidationStatus
from pydantic import BaseModel, Field, model_validator


class VerdictType(str, Enum):
    """The four verdicts (VERIFICATION_FRAMEWORK.md, Section 4)."""

    PASS = "PASS"
    PASS_WITH_CAUTION = "PASS WITH CAUTION"
    FLAG = "FLAG"
    REJECT = "REJECT"


class FailureCategory(str, Enum):
    """
    The five failure categories VERIFICATION_FRAMEWORK.md Section 5.7
    names as examples of what a FLAG or REJECT should classify *why* it
    failed as: "(data quality, model disagreement, staleness, missing
    dependency, unverifiable provenance) so a FLAG or REJECT is
    actionable, not a generic rejection."
    """

    DATA_QUALITY = "DATA_QUALITY"
    MODEL_DISAGREEMENT = "MODEL_DISAGREEMENT"
    STALENESS = "STALENESS"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    UNVERIFIABLE_PROVENANCE = "UNVERIFIABLE_PROVENANCE"


class Verdict(BaseModel):
    """
    The outcome of a Stage 11 independent check
    (VERIFICATION_FRAMEWORK.md, Section 4). `reasons` is a list, not a
    single string, because multiple independent checks can fail
    simultaneously and every failure should be reported, not just the
    first one found.
    """

    verdict_type: VerdictType
    reasons: list[str] = Field(default_factory=list)
    failure_category: Optional[FailureCategory] = Field(
        default=None,
        description=(
            "Set for FLAG/REJECT verdicts (Section 5.7's failure "
            "classification). Left None for PASS/PASS WITH CAUTION."
        ),
    )
    flagged_status: Optional[ValidationStatus] = Field(
        default=None,
        description=(
            "Required when verdict_type=FLAG: which of CONFLICTED, "
            "STALE, or INCOMPLETE applies "
            '(VERIFICATION_FRAMEWORK.md Section 4: "validation_status '
            'becomes CONFLICTED, STALE, or INCOMPLETE as appropriate to '
            'the specific issue found"). Not used for other verdict types.'
        ),
    )

    @model_validator(mode="after")
    def _flag_must_specify_flagged_status(self) -> "Verdict":
        if self.verdict_type == VerdictType.FLAG:
            if self.flagged_status not in (
                ValidationStatus.CONFLICTED,
                ValidationStatus.STALE,
                ValidationStatus.INCOMPLETE,
            ):
                raise ValueError(
                    "Verdict: a FLAG verdict must set flagged_status to "
                    "one of CONFLICTED, STALE, or INCOMPLETE "
                    "(VERIFICATION_FRAMEWORK.md, Section 4)."
                )
        return self
