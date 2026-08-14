import pytest

from optifi_ai.verification_gate import apply_gate, CIOVerdictHandling, map_verdict_to_handling
from optifi_shared import ValidationStatus
from optifi_verification import Verdict, VerdictType


def test_pass_maps_to_pass():
    v = Verdict(verdict_type=VerdictType.PASS, reasons=["ok"])
    assert map_verdict_to_handling(v) == CIOVerdictHandling.PASS


def test_pass_with_caution_maps_to_pass_with_caution():
    v = Verdict(verdict_type=VerdictType.PASS_WITH_CAUTION, reasons=["caution"])
    assert map_verdict_to_handling(v) == CIOVerdictHandling.PASS_WITH_CAUTION


def test_flag_conflicted_maps_to_revise():
    v = Verdict(verdict_type=VerdictType.FLAG, reasons=["conflict"], flagged_status=ValidationStatus.CONFLICTED)
    assert map_verdict_to_handling(v) == CIOVerdictHandling.REVISE


def test_flag_stale_maps_to_revise():
    v = Verdict(verdict_type=VerdictType.FLAG, reasons=["stale"], flagged_status=ValidationStatus.STALE)
    assert map_verdict_to_handling(v) == CIOVerdictHandling.REVISE


def test_flag_incomplete_maps_to_insufficient_evidence():
    v = Verdict(verdict_type=VerdictType.FLAG, reasons=["missing corroboration"], flagged_status=ValidationStatus.INCOMPLETE)
    assert map_verdict_to_handling(v) == CIOVerdictHandling.INSUFFICIENT_EVIDENCE


def test_reject_maps_to_reject():
    v = Verdict(verdict_type=VerdictType.REJECT, reasons=["loss cap violated"])
    assert map_verdict_to_handling(v) == CIOVerdictHandling.REJECT


def test_apply_gate_reject_excludes_regardless_of_other_passing_verdicts():
    verdicts = [
        Verdict(verdict_type=VerdictType.PASS, reasons=["check A ok"]),
        Verdict(verdict_type=VerdictType.REJECT, reasons=["check B failed"]),
    ]
    result = apply_gate(verdicts)
    assert result.handling == CIOVerdictHandling.REJECT
    assert result.excluded is True


def test_apply_gate_worst_of_several_non_reject_verdicts_wins():
    verdicts = [
        Verdict(verdict_type=VerdictType.PASS, reasons=["ok"]),
        Verdict(verdict_type=VerdictType.FLAG, reasons=["incomplete"], flagged_status=ValidationStatus.INCOMPLETE),
    ]
    result = apply_gate(verdicts)
    assert result.handling == CIOVerdictHandling.INSUFFICIENT_EVIDENCE
    assert result.excluded is False


def test_apply_gate_requires_at_least_one_verdict():
    with pytest.raises(ValueError):
        apply_gate([])


def test_apply_gate_preserves_all_reasons():
    verdicts = [
        Verdict(verdict_type=VerdictType.PASS, reasons=["reason A"]),
        Verdict(verdict_type=VerdictType.PASS_WITH_CAUTION, reasons=["reason B"]),
    ]
    result = apply_gate(verdicts)
    assert "reason A" in result.reasons
    assert "reason B" in result.reasons
