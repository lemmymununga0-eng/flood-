"""Persistence for `DataSource` connectivity-check results. Wraps the exact
mutate/commit/refresh sequence that used to sit inline in
`app/services/data_source_health.py`.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.data_source import DataSource


class DataSourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_check_result(self, source: DataSource, status: str, detail: str) -> DataSource:
        source.last_check_status = status
        source.last_check_detail = detail
        source.last_checked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(source)
        return source
