"""Real connectivity checks for the data-source catalog. Mirrors the honesty rule in
app/services/weather_ingestion.py: on failure, the actual exception is stored, never a
fabricated "operational" status. A failure here (this sandbox's egress policy blocks
NASA POWER and DMMU's site has a redirect-loop issue — see docs/DATA-SOURCES.md) is
expected in this environment and is not silently hidden.

The actual HTTP probe and persistence are delegated to
`app.integrations.http_health_checker` and `app.repositories.data_source_repository`
respectively — this module is pure orchestration so a test can inject a fake checker
without a network dependency."""
from sqlalchemy.orm import Session

from app.integrations.http_health_checker import HttpHealthChecker
from app.models.data_source import DataSource
from app.repositories.data_source_repository import DataSourceRepository


def check_data_source(db: Session, source: DataSource, checker: HttpHealthChecker, timeout_s: float = 8.0) -> DataSource:
    repo = DataSourceRepository(db)

    if not source.base_url:
        return repo.save_check_result(source, "unknown", "No base_url configured for this source.")

    outcome = checker.probe(source.base_url, timeout_s=timeout_s)
    return repo.save_check_result(source, outcome.status, outcome.detail)
