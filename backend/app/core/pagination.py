"""Shared pagination params for list endpoints. Additive only — default values return
the full (small, real) dataset this project currently has, so existing frontend calls
that don't pass query params are unaffected; larger real datasets (once ingestion
scales up) get real limit/offset control rather than always returning everything."""
from dataclasses import dataclass

from fastapi import Query


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination_params(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)
