"""
The Universal Analytical Packet (UAP).

Source specification: ANALYTICAL_CONTRACT_SPEC.md, Section 5 ("The
Universal Analytical Packet — Field Definitions"), which is the
authoritative, conceptual field list this module gives concrete types to.
`information_class` values come from Section 3; `validation_status` values
come from Section 4.

Section 5 is explicit that it describes "a conceptual field list — names
and meanings, not types, defaults, or storage format." This module is
where those types and defaults are first pinned down; the choices made
here (e.g. `confidence` as a three-level qualitative enum, matching
`APP_UX_BLUEPRINT.md` Section 13's "Confidence: Moderate" display
pattern) are implementation decisions, not restatements of the spec.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class InformationClass(str, Enum):
    """The three information classes (ANALYTICAL_CONTRACT_SPEC.md, Section 3)."""

    FACT = "FACT"
    ESTIMATE = "ESTIMATE"
    JUDGEMENT = "JUDGEMENT"


class ValidationStatus(str, Enum):
    """The seven validation_status values (ANALYTICAL_CONTRACT_SPEC.md, Section 4)."""

    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    CONFLICTED = "CONFLICTED"
    STALE = "STALE"
    INCOMPLETE = "INCOMPLETE"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class ConfidenceLevel(str, Enum):
    """
    Qualitative certainty level for UAP.confidence.

    ANALYTICAL_CONTRACT_SPEC.md Section 5 leaves confidence's type
    unspecified; this three-level enum matches the qualitative labels
    APP_UX_BLUEPRINT.md Section 13 already displays (e.g. "Confidence:
    Moderate"), rather than introducing a numeric score nothing in the
    specification calls for.
    """

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class UAP(BaseModel):
    """
    Universal Analytical Packet — ANALYTICAL_CONTRACT_SPEC.md, Section 5.

    Every OptiFi engine communicates using this shape. Field-by-field
    provenance to Section 5 is given in each field's description below.
    """

    model_config = ConfigDict(use_enum_values=False)

    # --- Identity & classification ---

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description=(
            "Section 5: 'a unique identifier for this specific packet "
            "instance, so other packets can reference it.' Auto-generated "
            "(UUID4) if not explicitly provided."
        ),
    )
    subject: str = Field(
        ...,
        description=(
            "Section 5: 'a stable identifier for the analytical question, "
            "quantity, or entity this packet answers.'"
        ),
    )
    information_class: InformationClass = Field(
        ...,
        description="Section 5 / Section 3: FACT, ESTIMATE, or JUDGEMENT.",
    )
    validation_status: ValidationStatus = Field(
        ...,
        description="Section 5 / Section 4: current trust level of this packet.",
    )

    # --- Content ---

    result: Any = Field(
        ...,
        description="Section 5: 'the conclusion or value itself.'",
    )

    # --- Provenance & timing ---

    source: str = Field(
        ...,
        description=(
            "Section 5: 'the external evidentiary origin (a data provider, "
            "a filing, a publication). Distinct from producer.'"
        ),
    )
    producer: str = Field(
        ...,
        description=(
            "Section 5: 'the internal OptiFi engine and methodology/model "
            "identity that generated this packet.'"
        ),
    )
    evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Section 5: 'pointer(s) to or description of the supporting "
            "evidence.' A list to accommodate corroboration (Section 4a), "
            "where an additional independent source is added to this field "
            "rather than replacing it — corroboration logic itself is not "
            "implemented here."
        ),
    )
    evidence_as_of: datetime | None = Field(
        default=None,
        description=(
            "Section 5: 'the point in time the underlying evidence or data "
            "refers to.'"
        ),
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description=(
            "Section 5: 'when this packet itself was produced.' Defaults "
            "to construction time, analogous to id's auto-generation."
        ),
    )

    # --- Uncertainty & reasoning ---

    confidence: ConfidenceLevel = Field(
        ...,
        description=(
            "Section 5: 'degree of certainty in the result.' A qualitative "
            "certainty level (LOW/MODERATE/HIGH), not free text — a caveat "
            "about the result belongs in `limitations`, not here."
        ),
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Section 5: 'assumptions made in producing the result.'",
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Section 5: 'known limitations of methodology or scope.'",
    )

    # --- Structural relationships ---

    dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "Section 5: 'the upstream inputs this result relied on.' "
            "Defaults to empty — a directly-sourced FACT typically has none."
        ),
    )
    provenance_chain: list[str] = Field(
        default_factory=list,
        description=(
            "Section 5: 'explicit references, by id, to the specific "
            "upstream packets this result was derived from.' Defaults to "
            "empty — a directly-sourced FACT typically has an empty or "
            "minimal chain (Section 6)."
        ),
    )
    disagreement_set_ref: str | None = Field(
        default=None,
        description=(
            "Section 5: optional. 'Where this packet is one of several "
            "competing answers to the same subject, a reference linking it "
            "to its siblings.'"
        ),
    )
    supersedes: list[str] = Field(
        default_factory=list,
        description=(
            "Section 5: optional. 'References the id of the earlier "
            "packet(s), sharing this packet's subject, that this packet "
            "officially replaces.' Not in this task's summarised field "
            "list, but present in Section 5 itself — included so the "
            "model covers every field Section 5 actually defines."
        ),
    )
