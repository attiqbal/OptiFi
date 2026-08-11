"""
CausalClaim — the structural contract every causal claim must satisfy,
regardless of which causal inference methodology eventually produces it.

Source specification: CAUSAL_ENGINE_SPEC.md, Section 5 ("Causal Claim
Requirements"). This module implements the *data contract* that document
describes — `cause_entity_id`/`effect_entity_id` (Section 5.1), the
mechanism-or-precedent guardrail (Section 5.2, restated in Section 6), and
the optional strength/time-lag fields (Sections 5.3/5.4). It does not
choose, implement, or stub out any causal inference algorithm — how a
`CausalClaim` gets produced remains exactly as undecided as
CAUSAL_ENGINE_SPEC.md Section 3 left it.

Design choice: `CausalClaim` *extends* `UAP` (subclassing) rather than
wrapping it. A causal claim is not a separate kind of object alongside a
UAP — CAUSAL_ENGINE_SPEC.md Section 5.5 says every claim "carries
information_class: ESTIMATE" as a UAP field, not as an attribute of some
enclosing structure. Subclassing keeps every existing UAP field (source,
confidence, provenance_chain, etc.) directly available without an extra
layer of indirection, while adding the causal-specific fields and the
guardrail as this subclass's own responsibility.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field, field_validator, model_validator

from optifi_shared import InformationClass, UAP


class CausalClaim(UAP):
    """
    A causal claim, per CAUSAL_ENGINE_SPEC.md Section 5.

    Enforces two things beyond the base UAP shape:

    1. `information_class` is always ESTIMATE
       (ENGINE_PIPELINE_SPECIFICATION.md, Stage 5 — causal-engine's
       output is never FACT or JUDGEMENT). Precisely: any value
       explicitly passed other than ESTIMATE is rejected at
       construction. The field's own default is hardcoded to ESTIMATE,
       so omitting it is equally safe — but be aware pydantic v2 does
       not re-run field_validators against a field left at its default
       value, only against explicitly-passed values. This validator has
       therefore never actually executed for any construction in this
       codebase to date, since every current caller relies on the
       default rather than passing information_class= explicitly; the
       invariant holds today because the default is correct, not
       because this check is continuously re-verifying it.
    2. The correlation-causation guardrail
       (CAUSAL_ENGINE_SPEC.md, Section 5.2 / Section 6): at least one of
       `mechanism` or `historical_precedent` must be present. Bare
       statistical correlation, with neither, must never be output as a
       causal claim — this is enforced here as a hard construction-time
       error, not a soft warning.
    """

    information_class: InformationClass = Field(
        default=InformationClass.ESTIMATE,
        description=(
            "Fixed to ESTIMATE for every CausalClaim "
            "(ENGINE_PIPELINE_SPECIFICATION.md, Stage 5). Any value "
            "explicitly passed other than ESTIMATE is rejected at "
            "construction; see the class docstring for the pydantic "
            "defaulted-field nuance this implies."
        ),
    )

    cause_entity_id: str = Field(
        ...,
        description=(
            "CAUSAL_ENGINE_SPEC.md Section 5.1: the ECONOMIC_ONTOLOGY.md "
            "entity identifier for the cause. A plain string identifier "
            "for now, since ECONOMIC_ONTOLOGY.md is not yet implemented "
            "as code."
        ),
    )
    effect_entity_id: str = Field(
        ...,
        description=(
            "CAUSAL_ENGINE_SPEC.md Section 5.1: the ECONOMIC_ONTOLOGY.md "
            "entity identifier for the effect."
        ),
    )
    mechanism: Optional[str] = Field(
        default=None,
        description=(
            "CAUSAL_ENGINE_SPEC.md Section 5.2: 'a plausible, explicitly "
            "stated economic mechanism connecting cause to effect.' One "
            "of mechanism or historical_precedent is required — see the "
            "guardrail validator below."
        ),
    )
    historical_precedent: Optional[str] = Field(
        default=None,
        description=(
            "CAUSAL_ENGINE_SPEC.md Section 5.2: description of prior "
            "instances where this relationship has held. One of "
            "mechanism or historical_precedent is required."
        ),
    )
    relationship_strength: Optional[str] = Field(
        default=None,
        description=(
            "CAUSAL_ENGINE_SPEC.md Section 5.3: magnitude/strength where "
            "expressible. Free text for now — no quantification method "
            "is chosen here."
        ),
    )
    time_lag: Optional[str] = Field(
        default=None,
        description=(
            "CAUSAL_ENGINE_SPEC.md Section 5.4: expected delay between "
            "cause and effect."
        ),
    )

    @field_validator("information_class")
    @classmethod
    def _information_class_must_be_estimate(
        cls, value: InformationClass
    ) -> InformationClass:
        if value != InformationClass.ESTIMATE:
            raise ValueError(
                "CausalClaim.information_class must be ESTIMATE "
                "(ENGINE_PIPELINE_SPECIFICATION.md, Stage 5) — a causal "
                "claim is never FACT or JUDGEMENT."
            )
        return value

    @model_validator(mode="after")
    def _enforce_correlation_causation_guardrail(self) -> "CausalClaim":
        mechanism_present = bool(self.mechanism and self.mechanism.strip())
        precedent_present = bool(
            self.historical_precedent and self.historical_precedent.strip()
        )
        if not mechanism_present and not precedent_present:
            raise ValueError(
                "CausalClaim requires at least one of `mechanism` or "
                "`historical_precedent` (CAUSAL_ENGINE_SPEC.md, Section "
                "5.2, restated in Section 6: 'Bare statistical "
                "correlation, with neither a stated mechanism nor "
                "historical precedent, must never be output as a causal "
                "claim.')"
            )
        return self
