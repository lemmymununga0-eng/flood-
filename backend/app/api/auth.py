from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.database.session import get_db
from app.models.user import Role, User
from app.schemas.user import LoginInput, TokenOut, UserOut, UserRegisterInput

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserRegisterInput, db: Session = Depends(get_db)) -> TokenOut:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "email_taken", "message": "An account with this email already exists."},
        )
    citizen_role = db.scalar(select(Role).where(Role.name == "CITIZEN"))
    if citizen_role is None:
        # Roles must be seeded (scripts/seed_db.py) before registration can work — this
        # is a real precondition failure, not a fabricated success.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "roles_not_seeded", "message": "CITIZEN role does not exist. Run scripts/seed_db.py."},
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role_id=citizen_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    record_audit_event(db, user_id=user.id, action="user_registered", entity_type="user", entity_id=user.id)
    db.commit()
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=_user_out(user),
    )


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginInput, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_credentials", "message": "Incorrect email or password."},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "account_disabled", "message": "This account is disabled."},
        )
    record_audit_event(db, user_id=user.id, action="user_login", entity_type="user", entity_id=user.id)
    db.commit()
    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
        user=_user_out(user),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(current_user)
