"""
Illustrative usage of the UAP — not an engine implementation.

`example_sharpe_ratio_uap` demonstrates the UAP pattern working end-to-end
using the Sharpe ratio formula from QUANT_ENGINE_SPEC.md Section 5.2. It
does not constitute an implementation of `quant-engine`, which remains a
separate future task.
"""

from .uap import ConfidenceLevel, InformationClass, UAP, ValidationStatus


def example_sharpe_ratio_uap(
    portfolio_return: float,
    risk_free_rate: float,
    portfolio_std_dev: float,
) -> UAP:
    """
    Compute a Sharpe ratio (QUANT_ENGINE_SPEC.md, Section 5.2:
    `(R_p - R_f) / σ_p`) and return it wrapped in a UAP.

    Illustrative only.
    """
    sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std_dev

    # LOW, not MODERATE or HIGH: this is a single, non-corroborated
    # calculation on illustrative (not real, not cross-checked) inputs —
    # exactly the ANALYTICAL_CONTRACT_SPEC.md Section 4a scenario where a
    # single uncorroborated source keeps confidence low, since nothing here
    # has been verified against a second independent source.
    return UAP(
        subject="illustrative portfolio Sharpe ratio",
        information_class=InformationClass.ESTIMATE,
        validation_status=ValidationStatus.PROVISIONAL,
        result=sharpe_ratio,
        source="illustrative example — not a real data source",
        producer="quant-engine (illustrative) / Sharpe ratio, QUANT_ENGINE_SPEC.md Section 5.2",
        confidence=ConfidenceLevel.LOW,
        assumptions=[
            "portfolio_return, risk_free_rate, and portfolio_std_dev are "
            "expressed over the same period and are already annualised "
            "consistently with one another",
        ],
        limitations=[
            "illustrative only — not connected to any real portfolio data "
            "or a real quant-engine implementation",
        ],
    )
