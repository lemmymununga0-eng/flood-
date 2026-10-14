from fastapi import APIRouter, Response
from sqlalchemy import text

from app.database.session import SessionLocal
from app.ml.predictor import artifacts_available

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness only: the process is up. Cheap and dependency-free, so the platform
    health check never restarts the service because of a database blip."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response) -> dict:
    """Readiness: reports whether the database answers and the model artifacts load.
    Returns 503 when either is down, so a deploy can be verified rather than assumed."""
    checks: dict[str, str] = {}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001 - detail stays in server logs, not the response
        checks["database"] = "unavailable"
    checks["model"] = "ok" if artifacts_available() else "unavailable"
    ok = all(v == "ok" for v in checks.values())
    if not ok:
        response.status_code = 503
    return {"status": "ready" if ok else "degraded", **checks}
