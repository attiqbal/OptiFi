"""
optifi_replay — replay-engine.

Historical replay and decision reconstruction (Phase E5) — see this
package's README.md and ENGINE_PIPELINE_SPECIFICATION.md Section 12
item 7 for the ownership decision.
"""

from .decision_package import HistoricalDecisionPackage, run_replay
from .historical_periods import get_period, HistoricalPeriod, REPLAY_PERIODS
from .scorecard import DecisionScorecard, derive_risk_soundness, evaluate_replay
from .snapshot import build_snapshot, filter_available_scorecards, HistoricalSnapshot

__all__ = [
    "HistoricalPeriod",
    "REPLAY_PERIODS",
    "get_period",
    "HistoricalSnapshot",
    "build_snapshot",
    "filter_available_scorecards",
    "HistoricalDecisionPackage",
    "run_replay",
    "DecisionScorecard",
    "evaluate_replay",
    "derive_risk_soundness",
]
