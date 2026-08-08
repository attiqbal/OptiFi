"""
Tests for the Gap 2 provenance fix — optional covariance_source_id /
expected_returns_source_id parameters on minimize_variance and
minimize_variance_with_loss_cap.

optifi_verification is a [dev]/test-only dependency of this package (see
pyproject.toml), used only here to prove the fix's actual downstream
effect on verification-engine's check_provenance_resolvable — production
code in optifi_optimisation does not import it.

Note: the source ids are recorded in BOTH `dependencies` and
`provenance_chain`, not just `dependencies` as the fix request literally
said — see `_source_id_links`'s docstring in mean_variance.py for why
only `dependencies` would have left check_provenance_resolvable exactly
as vacuous as before (it reads provenance_chain, not dependencies).
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus
from optifi_verification import VerdictType, check_provenance_resolvable

from optifi_optimisation import minimize_variance, minimize_variance_with_loss_cap

EXPECTED_RETURNS = {"A": 0.05, "B": 0.08, "C": 0.12}
COVARIANCE = {
    "A": {"A": 0.04, "B": 0.0, "C": 0.0},
    "B": {"A": 0.0, "B": 0.09, "C": 0.0},
    "C": {"A": 0.0, "B": 0.0, "C": 0.16},
}
TARGET_RETURN = 0.09


def _make_known_uap(uap_id: str) -> UAP:
    return UAP(
        id=uap_id,
        subject="test upstream packet",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.VERIFIED,
        result="test",
        source="test source",
        producer="test producer",
        confidence=ConfidenceLevel.MODERATE,
    )


# --- minimize_variance: existing behaviour unaffected when omitted ---


def test_minimize_variance_dependencies_and_provenance_empty_when_source_ids_omitted():
    uap = minimize_variance(EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN)
    assert uap.dependencies == []
    assert uap.provenance_chain == []


def test_minimize_variance_records_both_source_ids_when_provided():
    uap = minimize_variance(
        EXPECTED_RETURNS,
        COVARIANCE,
        target_return=TARGET_RETURN,
        covariance_source_id="cov-uap-123",
        expected_returns_source_id="returns-uap-456",
    )
    assert set(uap.dependencies) == {"cov-uap-123", "returns-uap-456"}
    assert set(uap.provenance_chain) == {"cov-uap-123", "returns-uap-456"}


def test_minimize_variance_records_only_the_one_source_id_provided():
    uap = minimize_variance(
        EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN, covariance_source_id="cov-uap-123"
    )
    assert uap.dependencies == ["cov-uap-123"]
    assert uap.provenance_chain == ["cov-uap-123"]


# --- minimize_variance_with_loss_cap: same optional behaviour ---


def test_minimize_variance_with_loss_cap_dependencies_and_provenance_empty_when_omitted():
    uap = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=1_000_000.0,
        max_single_period_loss=1_000_000.0,
        confidence_level=0.95,
    )
    assert uap.dependencies == []
    assert uap.provenance_chain == []


def test_minimize_variance_with_loss_cap_records_both_source_ids_when_provided():
    uap = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=1_000_000.0,
        max_single_period_loss=1_000_000.0,
        confidence_level=0.95,
        covariance_source_id="cov-uap-789",
        expected_returns_source_id="returns-uap-abc",
    )
    assert set(uap.dependencies) == {"cov-uap-789", "returns-uap-abc"}
    assert set(uap.provenance_chain) == {"cov-uap-789", "returns-uap-abc"}


# --- The critical proof: check_provenance_resolvable is no longer vacuous ---


def test_provenance_check_passes_when_source_id_is_actually_known():
    real_cov_id = "cov-uap-real"
    candidate = minimize_variance(
        EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN, covariance_source_id=real_cov_id
    )
    known_packets = {real_cov_id: _make_known_uap(real_cov_id)}

    verdict = check_provenance_resolvable(candidate, known_packets)

    assert verdict.verdict_type == VerdictType.PASS


def test_provenance_check_is_no_longer_vacuous_a_broken_source_id_is_flagged():
    """
    Before the Gap 2 fix, minimize_variance's output always had an empty
    provenance_chain, so check_provenance_resolvable passed on every
    candidate vacuously — there was never anything to actually check.
    With a real covariance_source_id supplied but genuinely absent from
    known_packets (e.g. the covariance UAP was never persisted, or its id
    was typo'd upstream), the check must now REJECT — proof the check can
    fail, not just trivially pass.
    """
    broken_cov_id = "cov-uap-does-not-exist"
    candidate = minimize_variance(
        EXPECTED_RETURNS, COVARIANCE, target_return=TARGET_RETURN, covariance_source_id=broken_cov_id
    )
    known_packets: dict[str, UAP] = {}  # the id is genuinely absent — a real broken link

    verdict = check_provenance_resolvable(candidate, known_packets)

    assert verdict.verdict_type == VerdictType.REJECT
    assert any(broken_cov_id in reason for reason in verdict.reasons)


def test_provenance_check_flags_broken_link_for_loss_cap_variant_too():
    broken_returns_id = "returns-uap-missing"
    candidate = minimize_variance_with_loss_cap(
        EXPECTED_RETURNS,
        COVARIANCE,
        TARGET_RETURN,
        portfolio_value=1_000_000.0,
        max_single_period_loss=1_000_000.0,
        confidence_level=0.95,
        expected_returns_source_id=broken_returns_id,
    )

    verdict = check_provenance_resolvable(candidate, known_packets={})

    assert verdict.verdict_type == VerdictType.REJECT
    assert any(broken_returns_id in reason for reason in verdict.reasons)
