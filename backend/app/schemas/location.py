from pydantic import BaseModel, ConfigDict


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    province: str
    latitude: float
    longitude: float
    coordinate_confidence: str
    evidence_note: str
    evidence_source_url: str
