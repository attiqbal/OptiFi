"""
Structured, machine-readable analytical failures — Phase E1 hardening.

Every specialist engine already raises `ValueError` on invalid or
insufficient input. This module gives those failures a MACHINE-READABLE
category (a caller can branch on `except MissingInputFailure` or
`isinstance(exc, AnalyticalFailure) and exc.category`) rather than being
forced to parse an exception's message string to know what kind of
failure occurred.

Purely additive, never a breaking change: every exception here IS a
`ValueError` (subclassing it, not replacing it), so every existing
`pytest.raises(ValueError)` call anywhere in this codebase continues to
match unchanged, whether or not a given raise site has been migrated to
one of these specific categories. Existing bare `raise ValueError(...)`
call sites are not required to migrate — this module makes the specific
categories available; adopting them project-wide, call site by call
site, is a separate, later piece of work (see the Phase E1 deliverable's
migration notes), not something this module silently forces.

The founding rule this whole hierarchy exists to serve: never fabricate
an analytical value to avoid returning one of these. A specialist
engine's job when it genuinely cannot answer is to fail structurally and
say why, not to substitute a plausible-looking number.
"""

from __future__ import annotations


class AnalyticalFailure(ValueError):
    """
    Base class for every structured analytical failure category below.
    Still a `ValueError` — catching `ValueError`, as most of this
    codebase's existing tests already do, continues to work unchanged
    for any subclass of this.
    """

    category: str = "ANALYTICAL_FAILURE"


class MissingInputFailure(AnalyticalFailure):
    """A required input was not supplied at all — distinct from a
    supplied-but-invalid input (see the other categories below)."""

    category = "MISSING_INPUT"


class StaleInputFailure(AnalyticalFailure):
    """A required input exists but its freshness window has lapsed
    (`validation_status=STALE`, ANALYTICAL_CONTRACT_SPEC.md Section 4,
    or an equivalent staleness the caller detected) — the analysis
    cannot honestly proceed on data known to be stale."""

    category = "STALE_INPUT"


class ConflictedInputFailure(AnalyticalFailure):
    """A required input exists but carries unresolved disagreement
    (`validation_status=CONFLICTED`) that the calling analysis has no
    basis to resolve on its own — it must not silently pick a side."""

    category = "CONFLICTED_INPUT"


class InsufficientDataFailure(AnalyticalFailure):
    """Enough of the input is present to attempt the analysis, but not
    enough to produce a statistically or analytically meaningful result
    (e.g. too few observations for a sample statistic)."""

    category = "INSUFFICIENT_DATA"


class UnsupportedFailure(AnalyticalFailure):
    """The request is well-formed but describes something this engine
    does not (yet) support — distinct from malformed or insufficient
    input, which the other categories cover."""

    category = "UNSUPPORTED"


class OutOfDistributionFailure(AnalyticalFailure):
    """The input is plausible in shape but falls so far outside the
    range the underlying model/method was designed for that its output
    would not be a meaningful analytical claim."""

    category = "OUT_OF_DISTRIBUTION"


class ModelFailure(AnalyticalFailure):
    """The underlying model or solver itself failed to produce a result
    (e.g. a numerical solver errored or did not converge) — not a
    problem with the input, but with the computation itself."""

    category = "MODEL_FAILURE"


class VerificationFailure(AnalyticalFailure):
    """An independent verification step rejected this result. Distinct
    from the other categories, which describe why an engine could not
    produce a result at all — this describes a result that WAS
    produced, but that independent verification refused to certify."""

    category = "VERIFICATION_FAILURE"


# --- Phase E2 additions: raw-data-quality categories ---
#
# The eight categories above were introduced under Phase E1 as
# "Examples" of structured analytical failures (i.e. illustrative, not a
# closed enumeration) — Phase E2's own Stage 2 validation work
# (data-engine's `validation.py`) surfaces genuinely distinct failure
# modes specific to RAW DATA QUALITY, not analytical computation, that
# none of the eight above describe well. Adding them here, rather than
# force-fitting a currency mismatch into e.g. OUT_OF_DISTRIBUTION, keeps
# `category` an honest, specific signal. Purely additive: nothing about
# the eight existing categories changes.


class DuplicateObservationFailure(AnalyticalFailure):
    """Two records claim to be the same observation (same identifier,
    same observation_time) but disagree on their value — a genuine
    conflict, not a harmless re-send of identical data (which is
    de-duplicated silently, not raised as a failure at all)."""

    category = "DUPLICATE_OBSERVATION"


class CurrencyMismatchFailure(AnalyticalFailure):
    """An observation's stated currency/unit does not match what the
    caller expected — proceeding without resolving this would silently
    mix incompatible scales."""

    category = "CURRENCY_MISMATCH"


class DiscontinuityFailure(AnalyticalFailure):
    """An observation moved far enough from the prior observation in
    the same series, in too short a time, to be treated as a genuine
    data-quality concern (a fat-fingered price, a decimal-point error,
    a bad tick) rather than accepted at face value."""

    category = "DISCONTINUITY"


class TimestampInconsistencyFailure(AnalyticalFailure):
    """An observation's own timestamps are internally inconsistent
    (e.g. retrieved before it was observed) — a sign the record itself,
    or its metadata, cannot be trusted as given."""

    category = "TIMESTAMP_INCONSISTENCY"


class CalendarMismatchFailure(AnalyticalFailure):
    """An observation's timing does not match the expected
    exchange/release calendar (e.g. a market observation timestamped
    for a date the relevant exchange was closed)."""

    category = "CALENDAR_MISMATCH"


class ImpossibleValueFailure(AnalyticalFailure):
    """An observation's value is outside what is physically or
    definitionally possible for its kind (e.g. a negative price) —
    distinct from OutOfDistributionFailure, which describes a value
    that is possible in principle but implausible relative to a model's
    expected range."""

    category = "IMPOSSIBLE_VALUE"
