"""
Illustrative usage of the ensemble mechanism — not a real forecast.

`example_recession_probability_forecasts` returns three illustrative
forecast UAPs (econometric / ML / market-implied style, matching the
canonical disagreement example already used elsewhere in this project's
documentation) sharing one `subject` and `disagreement_set_ref`. These are
not real forecasts from any real model — they demonstrate the ensemble
functions' shape, not a real forecasting result.
"""

from optifi_shared import ConfidenceLevel, InformationClass, UAP, ValidationStatus

_SUBJECT = "illustrative: UK recession probability, 12-month horizon"
_DISAGREEMENT_SET_REF = "illustrative-uk-recession-probability-12m"


def example_recession_probability_forecasts() -> list[UAP]:
    """
    Three illustrative forecast UAPs for the same illustrative question,
    styled after econometric / ML / market-implied model families
    (FORECAST_ENGINE_SPEC.md Section 5) — not real forecasts.
    """
    return [
        UAP(
            subject=_SUBJECT,
            information_class=InformationClass.ESTIMATE,
            validation_status=ValidationStatus.PROVISIONAL,
            result=0.32,
            source="illustrative example — not a real data source",
            producer="forecast-engine (illustrative) / econometric model",
            confidence=ConfidenceLevel.MODERATE,
            limitations=["illustrative only — not a real forecast"],
            disagreement_set_ref=_DISAGREEMENT_SET_REF,
        ),
        UAP(
            subject=_SUBJECT,
            information_class=InformationClass.ESTIMATE,
            validation_status=ValidationStatus.PROVISIONAL,
            result=0.48,
            source="illustrative example — not a real data source",
            producer="forecast-engine (illustrative) / ML model",
            confidence=ConfidenceLevel.MODERATE,
            limitations=["illustrative only — not a real forecast"],
            disagreement_set_ref=_DISAGREEMENT_SET_REF,
        ),
        UAP(
            subject=_SUBJECT,
            information_class=InformationClass.ESTIMATE,
            validation_status=ValidationStatus.PROVISIONAL,
            result=0.21,
            source="illustrative example — not a real data source",
            producer="forecast-engine (illustrative) / market-implied model",
            confidence=ConfidenceLevel.MODERATE,
            limitations=["illustrative only — not a real forecast"],
            disagreement_set_ref=_DISAGREEMENT_SET_REF,
        ),
    ]


# Illustrative historical errors for the same three models, in the same
# order — not real accuracy figures.
EXAMPLE_HISTORICAL_ERRORS = [0.05, 0.08, 0.03]
