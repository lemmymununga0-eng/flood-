import html
import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Citizen reports are free text submitted by the public and are rendered back to
# moderators. React escapes on render today, so stored markup is inert in THIS
# client -- but storing it means any future consumer (an export, an email digest, a
# native app, a templated PDF) inherits the hazard. Sanitize at the boundary instead
# of relying on every downstream renderer to be careful.
_TAG_RE = re.compile(r"<[^>]*>")


def _strip_markup(value: str) -> str:
    """Remove HTML tags and decode entities, preserving the human text.

    Order matters, and the first version of this got it wrong. Stripping tags before
    decoding entities meant an entity-encoded payload contained no literal "<", matched
    nothing, and was then reconstituted into live markup by unescape() -- so
    "&lt;img src=x onerror=...&gt;" was stored as "<img src=x onerror=...>". Decoding
    first closes that. Iterating to a fixed point additionally defeats nested
    constructions like "<scr<x>ipt>", which a single pass collapses INTO a valid tag.

    The bound is belt-and-braces: the loop converges in one or two passes for any real
    input, and the cap stops a pathological one from spinning.
    """
    previous = None
    current = value
    for _ in range(8):
        if current == previous:
            break
        previous = current
        current = _TAG_RE.sub("", html.unescape(current))
    return current.strip()


class CitizenReportCreate(BaseModel):
    location_id: int | None = None
    description: str = Field(min_length=5)
    severity: str = "unknown"

    @field_validator("description")
    @classmethod
    def strip_markup(cls, v: str) -> str:
        cleaned = _strip_markup(v)
        if len(cleaned) < 5:
            raise ValueError(
                "description must contain at least 5 characters of actual text "
                "once HTML markup is removed"
            )
        return cleaned


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
