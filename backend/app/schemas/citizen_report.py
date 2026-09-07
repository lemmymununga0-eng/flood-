from datetime import datetime

from pydantic import BaseModel, Field


class CitizenReportCreate(BaseModel):
    location_id: int | None = None
    description: str = Field(min_length=5)
    severity: str = "unknown"


class CitizenReportOut(BaseModel):
    id: int
    reporter_user_id: int | None
    location_id: int | None
    description: str
    severity: str
    status: str
    submitted_at: datetime
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    review_note: str

    model_config = {"from_attributes": True}


class CitizenReportModerate(BaseModel):
    status: str = Field(pattern="^(verified|rejected)$")
    review_note: str = ""
