"""
optifi_data — data-engine.

Implements the corroboration mechanism (ANALYTICAL_CONTRACT_SPEC.md
Section 4a) — pure logic operating on UAP objects. No real or mock
external data source, and no Stage 1 (Data Acquisition) or Stage 2
(Validation & Normalisation) implementation, exists in this package —
those remain separate future work.
"""

from .corroboration import corroborate_fact

__all__ = ["corroborate_fact"]
