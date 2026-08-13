"""
Canonical source identity — Phase E1 hardening.

The flat `UAP.source: str` field (ANALYTICAL_CONTRACT_SPEC.md Section 5)
conflates several genuinely different concepts: the publication that
carried a record, who originally produced the underlying information,
an intermediary that merely redistributed it, the data vendor OptiFi
actually ingested it through, the official issuing body for structured
data, and the underlying originating document/event a story is about.
Several publications repeating the same originating wire story must not
count as independent corroboration (ANALYTICAL_CONTRACT_SPEC.md Section
4a) — distinguishing these concepts is what makes that determination
possible beyond string-matching on outlet names alone.

This is a deliberately bounded MVP abstraction, not an attempt at a
perfect global source graph: `SourceIdentity` is a per-record structured
annotation a caller MAY attach, not a registry, not an entity-resolution
system, and not a replacement for the existing bounded same-origin
string heuristic below (`normalize_source`/`same_origin`) — it composes
with that heuristic rather than replacing it, and remains additive: a
UAP without a `SourceIdentity` still works exactly as before, using
`source: str` and the string heuristic alone.

`normalize_source`/`same_origin` moved here (from data-engine's
corroboration module, where they originated) because they are now
shared infrastructure both the flat-string path AND `SourceIdentity`
comparison use — `data-engine.corroboration` re-exports both under their
original names for backward compatibility; nothing about its existing,
tested behaviour changes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


def normalize_source(source: str) -> str:
    return " ".join(source.strip().lower().split())


def same_origin(source_a: str, source_b: str) -> bool:
    """
    Bounded same-origin heuristic on two raw strings: normalizes
    case/whitespace, then treats an exact match or a substring match in
    either direction as the same origin (catching cases like "BBC" /
    "BBC News" / " bbc " that plainly name the same outlet but weren't
    written identically). Does NOT resolve genuinely different-looking
    names for the same real-world outlet that share no common substring
    (e.g. "British Broadcasting Corporation" vs "BBC") — real entity
    resolution is out of scope for this MVP.
    """
    normalized_a = normalize_source(source_a)
    normalized_b = normalize_source(source_b)
    if not normalized_a or not normalized_b:
        return normalized_a == normalized_b
    return normalized_a == normalized_b or normalized_a in normalized_b or normalized_b in normalized_a


class SourceIdentity(BaseModel):
    """
    Structured, per-record source identity. Every field but
    `publication` is optional — callers supply as much structure as they
    actually know; an unset field is not assumed to differ from another
    record's unset field (see `same_source_identity` below for exactly
    how absence is handled).
    """

    publication: str = Field(
        ...,
        description=(
            "The specific outlet/publication that carried this record "
            "(e.g. 'BBC News', 'Financial Times') — the closest "
            "structured analogue to UAP.source today."
        ),
    )
    originator: str | None = Field(
        default=None,
        description=(
            "Who/what ORIGINALLY produced the underlying information, "
            "if known and different from `publication` (e.g. a press "
            "release from 'HM Treasury' carried verbatim by several "
            "outlets, or a wire service like 'Reuters' whose report "
            "multiple publications republish)."
        ),
    )
    redistributor: str | None = Field(
        default=None,
        description=(
            "An intermediary that redistributed this record without "
            "being its original source (e.g. a news aggregator, a "
            "syndication feed) — distinct from `publication` (the "
            "outlet a human reader would see it under) and from "
            "`originator` (who actually produced it)."
        ),
    )
    vendor: str | None = Field(
        default=None,
        description=(
            "The data vendor OptiFi actually ingested this record "
            "through (e.g. a market-data or news-feed provider) — an "
            "infrastructure/pipeline fact, not a claim about the "
            "content's own editorial origin. Two records from the same "
            "`vendor` are NOT thereby the same origin; a vendor is a "
            "pipe, not a source."
        ),
    )
    issuer: str | None = Field(
        default=None,
        description=(
            "The official issuing body for structured/official data "
            "(e.g. 'ONS' for a statistics release, the reporting "
            "company itself for a regulatory filing) — the strongest "
            "possible origin signal when present, since an official "
            "issuer has no further 'originator' behind it."
        ),
    )
    originating_document_id: str | None = Field(
        default=None,
        description=(
            "A stable identifier for the underlying originating "
            "document or event (a wire-story id, a press-release id, a "
            "filing accession number) — when two records carry the "
            "SAME `originating_document_id`, that is a strictly "
            "stronger same-origin signal than any name-based comparison "
            "below, since it identifies the literal underlying artifact "
            "rather than inferring shared origin from outlet names."
        ),
    )


def _effective_origin_label(identity: SourceIdentity) -> str:
    """
    The single string that best represents "who is actually responsible
    for this information's content", for name-based comparison: prefer
    `issuer` (an official issuer has no further origin behind it), then
    `originator` (the party that actually produced the content, if
    named), then fall back to `publication` (all we have, if neither of
    the more specific fields is set). `redistributor`/`vendor` are
    deliberately never used here — a shared redistributor or a shared
    data vendor does NOT imply the same underlying origin (see their
    field docs above).
    """
    return identity.issuer or identity.originator or identity.publication


def same_source_identity(a: SourceIdentity, b: SourceIdentity) -> bool:
    """
    Determines whether two structured source identities represent the
    same underlying origin, per ANALYTICAL_CONTRACT_SPEC.md Section 4a's
    "two outlets both republishing the same wire report... does not
    count" rule:

    1. If both carry an `originating_document_id` and they match
       exactly, they are the same origin — the strongest possible
       signal, and decisive on its own regardless of what
       `publication`/`originator`/`issuer` say.
    2. If both carry an `originating_document_id` and they DIFFER, they
       are NOT the same origin, even if their effective origin labels
       would otherwise look similar — an explicit document identifier
       is more authoritative than a name-based heuristic and should not
       be overridden by it.
    3. Otherwise (at least one side has no `originating_document_id`),
       fall back to the bounded `same_origin` string heuristic on each
       side's effective origin label (`issuer` > `originator` >
       `publication`).
    """
    if a.originating_document_id is not None and b.originating_document_id is not None:
        return a.originating_document_id == b.originating_document_id

    return same_origin(_effective_origin_label(a), _effective_origin_label(b))
