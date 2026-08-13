"""
Canonical asset identity — Phase E2 hardening.

A ticker string alone is not a globally unique identifier: the same
ticker can mean different securities on different exchanges (e.g. "BP"
on the LSE vs. a different "BP" elsewhere), and tickers are reused over
time as companies delist/relist. This module gives every asset a
structured identity distinguishing ticker, exchange, security type,
currency, and issuer — matching this project's existing precedent
(`ECONOMIC_ONTOLOGY.md` Section 4: "every entity in this ontology has a
stable identifier") applied specifically to the market-data boundary,
not a new philosophy.

This is deliberately an MVP-scale identity model, not a full security
master: `isin` is optional (recorded when known, not required, not
verified against any external registry), and there is no attempt at
corporate-action-aware identity resolution (a ticker changing issuer
after a merger, for instance) — see the Phase E2 deliverable's open
questions.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """DATA_SOURCE_REGISTRY.md Category A's own asset list, as a
    controlled taxonomy."""

    EQUITY = "EQUITY"
    ETF = "ETF"
    BOND = "BOND"
    FX = "FX"
    COMMODITY = "COMMODITY"
    INDEX = "INDEX"


class AssetIdentity(BaseModel):
    """
    Canonical, structured asset identity. Two `AssetIdentity` instances
    represent the SAME asset only if `ticker`, `exchange`, and
    `asset_type` all match — a shared ticker alone is deliberately
    insufficient (see `asset_identity_conflicts` below for the check
    that enforces this at ingestion time).
    """

    ticker: str = Field(..., description="The raw ticker/symbol as quoted by the exchange or vendor.")
    exchange: str = Field(
        ...,
        description=(
            "The specific exchange/venue this ticker is quoted on (e.g. "
            "'LSE', 'NASDAQ'). A recognised MIC (Market Identifier Code) "
            "is preferred where known, but not enforced — which "
            "identifier scheme to standardise on is an open question, "
            "see the Phase E2 deliverable."
        ),
    )
    asset_type: AssetType
    currency: str = Field(..., description="ISO-style currency code this asset is quoted/settled in.")
    issuer: str | None = Field(
        default=None,
        description=(
            "The issuing entity, when applicable (a company for an "
            "equity, a government/corporation for a bond) — not "
            "meaningful for FX pairs or physical commodities, left None "
            "there."
        ),
    )
    isin: str | None = Field(
        default=None,
        description=(
            "Optional stronger identifier when known (ISIN or "
            "equivalent) — recorded, not verified against any external "
            "registry in this MVP."
        ),
    )

    @property
    def canonical_id(self) -> str:
        """A stable, human-inspectable string key for this asset:
        'EXCHANGE:TICKER' — deliberately excludes currency/asset_type
        from the string itself (both are still checked in equality
        comparisons below), since two entries with the same
        exchange+ticker but a genuine mismatch elsewhere is exactly the
        conflict `asset_identity_conflicts` exists to catch, not
        something that should silently produce two different string
        keys."""
        return f"{self.exchange}:{self.ticker}"

    def same_asset_as(self, other: "AssetIdentity") -> bool:
        """Two identities refer to the same underlying asset only if
        ticker, exchange, AND asset_type all agree — matching on
        ticker alone (even within the same exchange) is not sufficient,
        since a ticker can be reused for an unrelated instrument type
        over time."""
        return (
            self.ticker == other.ticker
            and self.exchange == other.exchange
            and self.asset_type == other.asset_type
        )


def asset_identity_conflicts(a: AssetIdentity, b: AssetIdentity) -> list[str]:
    """
    Detects a genuine identity CONFLICT: `a` and `b` share the same
    `canonical_id` (exchange+ticker) but disagree on something that
    should never differ for the same real asset (`asset_type`,
    `currency`, or a mismatched non-None `isin`). Returns a list of
    human-readable conflict descriptions — empty if there is no
    conflict (either they're genuinely the same asset, or they're
    unrelated assets with coincidentally different canonical_ids, which
    is not a conflict at all).

    This is the check required test category #8 ("asset identity
    conflicts") exercises: a caller ingesting from two different
    providers must be told explicitly when they disagree about what a
    shared ticker+exchange actually is, not have one silently overwrite
    the other.
    """
    if a.canonical_id != b.canonical_id:
        return []  # different canonical ids -- not a conflict, just different assets

    conflicts: list[str] = []
    if a.asset_type != b.asset_type:
        conflicts.append(
            f"asset_type mismatch for {a.canonical_id}: {a.asset_type!r} vs {b.asset_type!r}"
        )
    if a.currency != b.currency:
        conflicts.append(
            f"currency mismatch for {a.canonical_id}: {a.currency!r} vs {b.currency!r}"
        )
    if a.isin is not None and b.isin is not None and a.isin != b.isin:
        conflicts.append(f"isin mismatch for {a.canonical_id}: {a.isin!r} vs {b.isin!r}")
    return conflicts
