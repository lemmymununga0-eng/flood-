from datetime import datetime

from pydantic import BaseModel


class ModelVersionOut(BaseModel):
    id: int
    version: str
    model_type: str
    training_period_start: datetime
    training_period_end: datetime
    metrics_json: str
    is_active: bool
    registered_at: datetime

    model_config = {"from_attributes": True}
