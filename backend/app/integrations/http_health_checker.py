"""Generic HTTP reachability probe, used to check a data source's connectivity. Same
HEAD-then-GET-fallback logic that used to sit inline in
`app/services/data_source_health.py` — relocated behind a small class so it can be
swapped for a test double via FastAPI's `dependency_overrides`."""
from dataclasses import dataclass
from typing import Literal

import requests


@dataclass
class HealthProbeOutcome:
    status: Literal["ok", "failed"]
    detail: str


class HttpHealthChecker:
    def probe(self, url: str, timeout_s: float = 8.0) -> HealthProbeOutcome:
        try:
            resp = requests.head(url, timeout=timeout_s, allow_redirects=True)
            if resp.status_code >= 400:
                # Some hosts (e.g. NASA POWER's base domain) reject HEAD; retry with GET
                # before concluding failure.
                resp = requests.get(url, timeout=timeout_s, allow_redirects=True)
            return HealthProbeOutcome("ok" if resp.status_code < 400 else "failed", f"HTTP {resp.status_code}")
        except requests.RequestException as exc:
            return HealthProbeOutcome("failed", f"{type(exc).__name__}: {exc}")


def get_health_checker() -> HttpHealthChecker:
    return HttpHealthChecker()
