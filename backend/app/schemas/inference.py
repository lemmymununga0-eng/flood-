from datetime import datetime

from pydantic import BaseModel, Field


class RiskPredictionRequest(BaseModel):
    """A validated weather observation to score. Every field is required — the
    pipeline never imputes a missing weather value (see docs/DATA_SOURCE_AUDIT.md in
    the research bundle). Values are the six NASA POWER daily variables the production
    model was trained on."""

    location_id: int | None = Field(
        default=None,
        description="Optional: a real Location row id, used to resolve name/coordinates.",
    )
    location_name: str | None = Field(
        default=None, description="Used when location_id is not supplied."
    )
    precipitation_mm: float = Field(ge=0, description="PRECTOTCORR, mm/day")
    temperature_c: float = Field(description="T2M, mean temperature at 2m, °C")
    temperature_max_c: float = Field(
        description="T2M_MAX, real daily MAXIMUM at 2m, °C. Must not be the daily mean."
    )
    temperature_min_c: float = Field(
        description="T2M_MIN, real daily MINIMUM at 2m, °C. Must not be the daily mean."
    )
    relative_humidity_pct: float = Field(ge=0, le=100, description="RH2M, %")
    wind_speed_10m_ms: float = Field(
        ge=0,
        description=(
            "WS10M, daily mean wind speed at 10 m, m/s. This is NOT WS2M (2 m wind); "
            "the two differ by roughly 25-40% and the model was trained on the 10 m value."
        ),
    )
    observation_date: str | None = Field(
        default=None, description="Date of the observation (YYYY-MM-DD), for traceability."
    )


class FeatureContribution(BaseModel):
    feature: str
    contribution: float
    direction: str


class RiskPredictionResponse(BaseModel):
    location: str
    latitude: float | None
    longitude: float | None
    prediction_horizon_days: int
    risk_probability_raw: float
    risk_probability_calibrated: float
    risk_level: str
    would_alert_at_threshold: bool
    decision_threshold: float
    model_version: str
    generated_at: datetime
    observation_date: str | None
    target_window_start: str | None
    target_window_end: str | None
    feature_contract_version: str
    explanation: list[FeatureContribution]
    caveats: list[str]
