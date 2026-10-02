"""FloodShield Zambia backend.

Built out of the normal phase order at the user's explicit request (see
docs/ROADMAP.md, Phase 10), then substantially expanded under the "Complete Backend
Implementation & End-to-End Integration" build: real JWT auth + RBAC, Alembic
migrations, an expanded schema (users/roles, citizen reports, data-source catalog,
audit log), and a consistent error-response format. Still NOT a claim that Phase 10 is
fully complete — no trained model, no SHAP explanations, no alert delivery to an
external channel. See docs/backend/backend-architecture.md for the current, honest
state.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
# Starlette's base HTTPException, NOT fastapi's subclass. The router itself raises
# the base class for an unknown path or a disallowed method, so a handler registered
# only on fastapi.HTTPException never saw those and they escaped with Starlette's
# default {"detail": ...} body instead of this app's {"error", "message"} shape.
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    alerts,
    auth,
    citizen_reports,
    data_sources,
    flood_events,
    health,
    locations,
    model_registry,
    notifications,
    predictions,
    system_status,
    weather,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FloodShield Zambia backend started (environment=%s)", settings.environment)
    yield


app = FastAPI(
    title="FloodShield Zambia API",
    description=(
        "Flood-risk PREDICTIONS are model output; flood-event and weather data are "
        "OBSERVATIONS/reports — see docs/RESEARCH-METHODOLOGY.md. A trained model IS "
        "served, but it does not demonstrate skill beyond seasonal climatology "
        "(see docs/MODEL-EVALUATION.md); research use only, not for public warnings. "
        "Schema is "
        "managed by Alembic migrations (backend/alembic/) — run `alembic upgrade head` "
        "before starting the server; the app no longer auto-creates tables."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limited", "message": "Too many requests. Try again shortly."},
    )


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Centralized error shape: {"error": <machine code>, "message": <human text>}.
    Routes that already raise HTTPException with a dict detail pass through as-is;
    routes using the older plain-string detail (or FastAPI's own validation errors)
    are normalized here so every error response has the same shape.

    Registered on Starlette's base HTTPException so that router-level 404s and 405s --
    which Starlette raises directly, bypassing fastapi.HTTPException -- are normalized
    too. fastapi.HTTPException subclasses it, so route-raised errors still match."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        body = exc.detail
    else:
        body = {"error": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic/FastAPI request-validation failures (bad JSON shape, wrong type,
    failed constraint) get the same {"error", "message"} shape as every other error,
    plus the real per-field detail list — never swallowed or genericized away."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request failed validation.",
            # jsonable_encoder: a custom field_validator that raises puts the raised
            # exception object into each error's "ctx", which json.dumps cannot
            # serialize -- without this the 422 became a 500 inside the handler.
            "fields": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler for anything not already caught. Logs the real exception
    server-side and returns a generic message to the client — never fabricates a
    friendlier error or exposes a stack trace to the caller."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected server error occurred."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(locations.router, prefix=settings.api_v1_prefix)
app.include_router(flood_events.router, prefix=settings.api_v1_prefix)
app.include_router(weather.router, prefix=settings.api_v1_prefix)
app.include_router(predictions.router, prefix=settings.api_v1_prefix)
app.include_router(alerts.router, prefix=settings.api_v1_prefix)
app.include_router(citizen_reports.router, prefix=settings.api_v1_prefix)
app.include_router(notifications.router, prefix=settings.api_v1_prefix)
app.include_router(model_registry.router, prefix=settings.api_v1_prefix)
app.include_router(data_sources.router, prefix=settings.api_v1_prefix)
app.include_router(system_status.router, prefix=settings.api_v1_prefix)
