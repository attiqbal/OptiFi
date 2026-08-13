"""
optifi_shared — shared types and contracts used across OptiFi's analytical engines.

Implements the Universal Analytical Packet (UAP), the interchange format
every engine uses to communicate analytical output, as specified in
ANALYTICAL_CONTRACT_SPEC.md Section 5.
"""

from .failures import (
    AnalyticalFailure,
    ConflictedInputFailure,
    InsufficientDataFailure,
    MissingInputFailure,
    ModelFailure,
    OutOfDistributionFailure,
    StaleInputFailure,
    UnsupportedFailure,
    VerificationFailure,
)
from .payloads import (
    expect_payload,
    FailureResult,
    ForecastResult,
    FundamentalObservation,
    MacroObservation,
    MarketObservation,
    OptimisationResult,
    PortfolioAnalytics,
    RecommendationCandidate,
    RiskAnalytics,
    StructuredEvent,
)
from .source_identity import normalize_source, same_origin, same_source_identity, SourceIdentity
from .uap import ConfidenceLevel, InformationClass, supersede, UAP, ValidationStatus
from .validation_propagation import propagate_validation_status, worst_validation_status

__all__ = [
    "UAP",
    "InformationClass",
    "ValidationStatus",
    "ConfidenceLevel",
    "supersede",
    "AnalyticalFailure",
    "MissingInputFailure",
    "StaleInputFailure",
    "ConflictedInputFailure",
    "InsufficientDataFailure",
    "UnsupportedFailure",
    "OutOfDistributionFailure",
    "ModelFailure",
    "VerificationFailure",
    "SourceIdentity",
    "same_source_identity",
    "normalize_source",
    "same_origin",
    "worst_validation_status",
    "propagate_validation_status",
    "MarketObservation",
    "MacroObservation",
    "FundamentalObservation",
    "StructuredEvent",
    "ForecastResult",
    "PortfolioAnalytics",
    "RiskAnalytics",
    "OptimisationResult",
    "RecommendationCandidate",
    "FailureResult",
    "expect_payload",
]
