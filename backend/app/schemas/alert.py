from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    risk_level: str
    location_id: int
    message: str
    audience: str
    channels: str
    status: str
    valid_until: datetime | None
    created_at: datetime


class AlertCreate(BaseModel):
    title: str
    risk_level: str
    location_id: int
    message: str
    audience: str = ""
    channels: str = "Dashboard"
    valid_until: datetime | None = None
