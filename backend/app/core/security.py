"""Password hashing and JWT issuance/verification. Real bcrypt hashing (the `bcrypt`
library directly — passlib's bcrypt backend is incompatible with bcrypt>=4.1 as of
this build, see docs/PROJECT-MEMORY.md) and real signed JWTs (python-jose) — no
placeholder/mock auth. Tokens are signed with `settings.secret_key`; see
.env.example for the requirement to override this outside local development.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt has a hard 72-byte input limit; truncate deterministically rather than error,
# matching common practice (and documented here so it's not a silent surprise).
_MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    pw_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash (e.g. legacy/unrecognized format) — never a match.
        return False


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """Returns the decoded payload, or None if the token is invalid/expired/malformed.
    Callers must check `payload["type"]` themselves if they need a specific token kind
    — this function does not distinguish access vs refresh."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
