from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    notification_type: str
    entity_type: str
    entity_id: int | None
    title: str
    message: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime
