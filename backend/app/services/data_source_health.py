"""Real connectivity checks for the data-source catalog. Mirrors the honesty rule in
app/services/weather_ingestion.py: on failure, the actual exception is stored, never a
fabricated "operational" status. Failures are not hidden — as of 2026-09-25, NASA POWER
and WARMA respond successfully from this machine while DMMU's site refuses connections.

The actual HTTP probe and persistence are delegated to
`app.integrations.http_health_checker` and `app.repositories.data_source_repository`
respectively — this module is pure orchestration so a test can inject a fake checker
without a network dependency."""
from sqlalchemy.orm import Session

from app.integrations.http_health_checker import HttpHealthChecker
from app.models.data_source import DataSource
from app.repositories.data_source_repository import DataSourceRepository


# Some catalogued sources are parameterised APIs that reject a bare base-URL request
# (NASA POWER answers HTTP 422 with no query string). Probing the base URL would record
# a "failure" for an API that is actually working, which would be misleading. For those,
# probe a real, minimal, valid request instead. The probe is still a genuine live HTTP
# call — this only fixes WHICH url is called, never how the result is interpreted.
PROBE_OVERRIDES = {
    "power.larc.nasa.gov": (
        "?parameters=T2M&community=AG&longitude=28.28&latitude=-15.42"
        "&start=20240101&end=20240102&format=JSON"
    ),
}


def _probe_url(base_url: str) -> str:
    for host, query in PROBE_OVERRIDES.items():
        if host in base_url and "?" not in base_url:
            return base_url.rstrip("/") + query
    return base_url


def check_data_source(db: Session, source: DataSource, checker: HttpHealthChecker, timeout_s: float = 8.0) -> DataSource:
    repo = DataSourceRepository(db)

    if not source.base_url:
        return repo.save_check_result(source, "unknown", "No base_url configured for this source.")

    outcome = checker.probe(_probe_url(source.base_url), timeout_s=timeout_s)
    return repo.save_check_result(source, outcome.status, outcome.detail)
