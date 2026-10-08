from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.sms import E164, normalise


class SubscriberCreate(BaseModel):
    phone: str
    name: str = ""
    location_id: int | None = None  # None = every area

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, v: str) -> str:
        v = normalise(v)
        if not E164.match(v):
            raise ValueError("Use international format, e.g. +260971234567")
        return v

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        return v.strip()[:120]


class SubscriberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    name: str
    location_id: int | None
    active: bool
    created_at: datetime
