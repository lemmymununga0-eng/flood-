from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.sms import E164, normalise


class SubscriberCreate(BaseModel):
    phone: str
    name: str = ""
    location_id: int | None = None  # None = every area
    # The administrator confirms the person agreed to receive flood-alert SMS. Required.
    consent: bool  # required: no default, so an omitted field is a 422, never a silent False
    consent_note: str = ""  # how/when consent was given, e.g. "verbal, 2026-10-10"

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

    @field_validator("consent_note")
    @classmethod
    def _clean_note(cls, v: str) -> str:
        return v.strip()[:200]

    @field_validator("consent")
    @classmethod
    def _consent_required(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Explicit consent is required before a number can be registered")
        return v


class ConsentIn(BaseModel):
    """Re-subscribing an opted-out number needs fresh, explicit consent."""

    consent: bool
    consent_note: str = ""

    @field_validator("consent")
    @classmethod
    def _consent_required(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Explicit consent is required")
        return v


class SubscriberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    name: str
    location_id: int | None
    active: bool
    consent_at: datetime | None
    consent_note: str
    opted_out_at: datetime | None
    created_at: datetime
    can_receive: bool
