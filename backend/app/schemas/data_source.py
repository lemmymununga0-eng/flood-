from datetime import datetime

from pydantic import BaseModel


class DataSourceOut(BaseModel):
    id: int
    name: str
    category: str
    base_url: str
    description: str
    last_checked_at: datetime | None
    last_check_status: str
    last_check_detail: str

    model_config = {"from_attributes": True}
