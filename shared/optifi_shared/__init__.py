"""
optifi_shared — shared types and contracts used across OptiFi's analytical engines.

Implements the Universal Analytical Packet (UAP), the interchange format
every engine uses to communicate analytical output, as specified in
ANALYTICAL_CONTRACT_SPEC.md Section 5.
"""

from .uap import ConfidenceLevel, InformationClass, UAP, ValidationStatus

__all__ = ["UAP", "InformationClass", "ValidationStatus", "ConfidenceLevel"]
