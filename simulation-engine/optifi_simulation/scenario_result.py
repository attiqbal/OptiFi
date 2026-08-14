"""
ScenarioResult — the structural contract every scenario simulation output
must satisfy, regardless of which propagation algorithm eventually
produces it.

Source specification: SIMULATION_ENGINE_SPEC.md, Section 7 ("Output:
Asset-Class / Sector-Level Impact") and Section 8 ("Uncertainty &
Sensitivity Analysis"). This module implements the *data contract* those
sections describe. It does not implement, choose, or stub out any
scenario propagation algorithm — SIMULATION_ENGINE_SPEC.md Section 6
explicitly inherits CAUSAL_ENGINE_SPEC.md's methodology-agnosticism, and
this module leaves that exactly as undecided.

Design choice: `ScenarioResult` *extends* `UAP` (subclassing), the same
choice `CausalClaim` made and for the same reason — a scenario result is
not a separate kind of object alongside a UAP, it is a UAP whose
`information_class` is fixed to `ESTIMATE` (Section 7) with additional
required structure layered on top. Subclassing keeps every existing UAP
field (source, confidence, provenance_chain, etc.) directly available
without an extra layer of indirection, consistent with the precedent
`causal-engine`'s `CausalClaim` already established for this project.
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from optifi_shared import InformationClass, UAP


class ScenarioResult(UAP):
    """
    A scenario simulation result, per SIMULATION_ENGINE_SPEC.md Sections
    7 and 8.

    Enforces three things beyond the base UAP shape:

    1. `information_class` is always ESTIMATE (SIMULATION_ENGINE_SPEC.md
       Section 7 — scenario output is never FACT or JUDGEMENT).
       Precisely: any value explicitly passed other than ESTIMATE is
       rejected at construction. The field's own default is hardcoded
       to ESTIMATE, so omitting it is equally safe — but be aware
       pydantic v2 does not re-run field_validators against a field
       left at its default value, only against explicitly-passed
       values. This validator has therefore never actually executed for
       any construction in this codebase to date, since every current
       caller relies on the default rather than passing
       information_class= explicitly; the invariant holds today because
       the default is correct, not because this check is continuously
       re-verifying it.
    2. The mandatory-range guardrail (SIMULATION_ENGINE_SPEC.md Section 8:
       "every simulation output carries a base case plus a range, not a
       single value"): `range_low` and `range_high` are both required
       fields — a ScenarioResult with only `base_case` and no range
       cannot be constructed. This is enforced the same way `CausalClaim`
       makes its own primary guardrail unambiguous: a hard
       construction-time error, not a soft default.
    3. A range-contains-base-case sanity check (`range_low <= base_case
       <= range_high`) — this is a reasonable addition made here, not a
       requirement SIMULATION_ENGINE_SPEC.md explicitly states the way it
       states the range-must-exist requirement.
    4. PHASE E4 addition — the range must have genuine width
       (`range_low < range_high`, strictly): Part 5's "Do not produce one
       deterministic 'future portfolio value.'" A `range_low == range_high`
       "range" satisfies guardrail 2's mere existence check but expresses
       zero actual uncertainty — a single number wearing a range-shaped
       costume. No genuine real-world scenario has zero width; this
       tightening has no legitimate use case to break, and directly
       enables the Testing Requirement "deterministic single-number
       simulation."
    """

    information_class: InformationClass = Field(
        default=InformationClass.ESTIMATE,
        description=(
            "Fixed to ESTIMATE for every ScenarioResult "
            "(SIMULATION_ENGINE_SPEC.md, Section 7). Any value "
            "explicitly passed other than ESTIMATE is rejected at "
            "construction; see the class docstring for the pydantic "
            "defaulted-field nuance this implies."
        ),
    )

    scenario_description: str = Field(
        ...,
        description=(
            "SIMULATION_ENGINE_SPEC.md Section 5: the perturbation being "
            "simulated (e.g. 'UK base rate: -100bp')."
        ),
    )
    affected_entity_id: str = Field(
        ...,
        description=(
            "SIMULATION_ENGINE_SPEC.md Section 7: the ECONOMIC_ONTOLOGY.md "
            "asset-class or sector entity this result concerns. A plain "
            "string identifier for now, consistent with how CausalClaim "
            "references entities."
        ),
    )
    base_case: float = Field(
        ...,
        description="SIMULATION_ENGINE_SPEC.md Section 8: the central estimate of impact.",
    )
    range_low: float = Field(
        ...,
        description=(
            "SIMULATION_ENGINE_SPEC.md Section 8: the low end of the "
            "mandatory uncertainty range. Required — a ScenarioResult "
            "with a base_case but no range is rejected."
        ),
    )
    range_high: float = Field(
        ...,
        description=(
            "SIMULATION_ENGINE_SPEC.md Section 8: the high end of the "
            "mandatory uncertainty range. Required, for the same reason "
            "as range_low."
        ),
    )
    sensitivity_factors: list[str] = Field(
        ...,
        description=(
            "SIMULATION_ENGINE_SPEC.md Section 8: which input assumptions "
            "the outcome depends on most heavily. Must be explicitly "
            "provided by the caller — an empty list is acceptable, but "
            "unlike UAP's own assumptions/limitations fields, this is not "
            "silently defaulted when omitted."
        ),
    )

    @field_validator("information_class")
    @classmethod
    def _information_class_must_be_estimate(
        cls, value: InformationClass
    ) -> InformationClass:
        if value != InformationClass.ESTIMATE:
            raise ValueError(
                "ScenarioResult.information_class must be ESTIMATE "
                "(SIMULATION_ENGINE_SPEC.md, Section 7) — a scenario "
                "result is never FACT or JUDGEMENT."
            )
        return value

    @model_validator(mode="after")
    def _range_must_contain_base_case(self) -> "ScenarioResult":
        # Reasonable addition, not spec-mandated the way the range's mere
        # existence is (Section 8) — see the class docstring, item 3.
        if not (self.range_low <= self.base_case <= self.range_high):
            raise ValueError(
                f"ScenarioResult: range [{self.range_low}, "
                f"{self.range_high}] does not contain base_case "
                f"({self.base_case}) — an uncertainty range that doesn't "
                "cover its own central estimate is internally "
                "inconsistent."
            )
        return self

    @model_validator(mode="after")
    def _range_must_have_genuine_width(self) -> "ScenarioResult":
        # PHASE E4 addition — see the class docstring, item 4.
        if self.range_low == self.range_high:
            raise ValueError(
                f"ScenarioResult: range_low == range_high == "
                f"{self.range_low} — a zero-width 'range' expresses no "
                "genuine uncertainty (PHASE E4 Part 5: 'Do not produce "
                "one deterministic future value.'). If the true "
                "uncertainty around this estimate is genuinely "
                "unknown, that is itself a limitation to state in "
                "`limitations`, not a reason to collapse the range to a "
                "point."
            )
        return self
