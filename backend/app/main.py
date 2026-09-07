"""FloodShield Zambia backend — early skeleton (see docs/ROADMAP.md, Phase 10).

Built ahead of the normal phase order at the user's explicit request, to demonstrate a
real running system on top of the real (small, incomplete) data gathered in Phase 1.
This is NOT a claim that Phase 10/11/12 are complete — no auth, no alerts, no citizen
reports, no trained model, minimal tests. See docs/ROADMAP.md for what's actually done.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import flood_events, health, locations, predictions, weather
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import Base, engine

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="FloodShield Zambia API",
    description=(
        "Early development skeleton. Flood-risk PREDICTIONS are model output; "
        "flood-event and weather data below are OBSERVATIONS/reports — see "
        "docs/RESEARCH-METHODOLOGY.md. No trained model exists yet, so /predictions "
        "legitimately returns an empty list."
    ),
    version="0.1.0-skeleton",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(locations.router, prefix=settings.api_v1_prefix)
app.include_router(flood_events.router, prefix=settings.api_v1_prefix)
app.include_router(weather.router, prefix=settings.api_v1_prefix)
app.include_router(predictions.router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("FloodShield Zambia backend started (environment=%s)", settings.environment)
