from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    model_version_id: int
    predicted_at: datetime
    prediction_probability: float
    risk_level: str
    prediction_horizon: str
    explanation: str
