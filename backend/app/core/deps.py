"""Shared FastAPI dependencies: current-user resolution and role-based access control.
Real DB lookups against the `users`/`roles` tables — no hardcoded/mock users."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database.session import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

ROLE_NAMES = ["ADMIN", "ANALYST", "OPERATOR", "RESEARCHER", "CITIZEN"]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "not_authenticated", "message": "Missing bearer token."},
        )
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Token is invalid or expired."},
        )
    user_id_raw = payload.get("sub")
    user = db.get(User, int(user_id_raw)) if user_id_raw is not None else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_user", "message": "User not found or inactive."},
        )
    return user


def require_roles(*allowed_role_names: str):
    """Dependency factory: `Depends(require_roles("ADMIN", "ANALYST"))`. Checks the
    authenticated user's real role row — never trusts a role claim embedded in the
    token itself, since roles can change after a token is issued."""

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in allowed_role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": f"Role '{user.role.name}' is not permitted to perform this action.",
                },
            )
        return user

    return _check
