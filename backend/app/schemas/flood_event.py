from datetime import date

from pydantic import BaseModel, ConfigDict


class FloodEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    start_date: date
    end_date: date | None
    provinces: str
    districts: str
    rivers: str
    impact_note: str
    deaths: int | None
    source_name: str
    source_url: str
    confidence_notes: str
