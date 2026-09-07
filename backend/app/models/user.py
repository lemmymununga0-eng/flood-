from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Role(Base):
    """One of the five roles defined by the governing prompt: ADMIN, ANALYST,
    OPERATOR, RESEARCHER, CITIZEN. Seeded once by `scripts/seed_db.py` — not
    user-creatable via the API, since the role set is fixed by the project design,
    not arbitrary."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    """A real, authenticated account. Passwords are bcrypt-hashed (never stored or
    logged in plaintext — see app/core/security.py). No user is seeded with a known
    default password in any environment other than local development
    (see scripts/seed_db.py, which prints the dev password once instead of hardcoding
    it in docs)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(160), default="")
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    role: Mapped["Role"] = relationship(back_populates="users")
