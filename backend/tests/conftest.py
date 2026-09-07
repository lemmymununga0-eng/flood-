"""Shared pytest fixtures. Tests run against a REAL PostgreSQL database
(`floodshield_zambia_test`, a separate database from the development
`floodshield_zambia` — never the dev/prod data), per this project's no-SQLite-
substitution rule. Each test function runs inside a transaction that is rolled back
afterward, so tests never leak state into each other and the test DB stays empty
between runs without needing a full drop/recreate every time.

Requires a local Postgres instance and a role that can connect to
`floodshield_zambia_test` (see docs/backend/backend-architecture.md, "Running the
tests"). If that database doesn't exist yet, create it once:
    psql -c "CREATE DATABASE floodshield_zambia_test OWNER floodshield;"
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://floodshield:changeme_dev_only@localhost:5432/floodshield_zambia_test",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.database.session import Base, get_db
from app.main import app
from app.models.location import Location
from app.models.user import Role

settings = get_settings()
test_engine = create_engine(settings.database_url)
TestSessionLocal = sessionmaker(bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db() -> Session:
    """A DB session bound to an outer transaction that is always rolled back at the
    end of the test — even though route handlers call session.commit() internally.
    Uses the standard SQLAlchemy SAVEPOINT-restart pattern so nothing a test does
    (including going through real API endpoints that commit) ever lands in the test
    database permanently."""
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> TestClient:
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    # Rate limiting itself is exercised by test_rate_limiting.py, which re-enables it
    # explicitly; every other test disables it so repeated calls (e.g. registering
    # many users across many tests within the same minute) aren't spuriously limited.
    app.state.limiter.enabled = False
    with TestClient(app) as c:
        yield c
    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_roles(db: Session) -> dict[str, Role]:
    roles = {}
    for name in ["ADMIN", "ANALYST", "OPERATOR", "RESEARCHER", "CITIZEN"]:
        role = Role(name=name, description=f"{name} role")
        db.add(role)
        db.flush()
        roles[name] = role
    db.commit()
    return roles


@pytest.fixture()
def seeded_location(db: Session) -> Location:
    loc = Location(
        name="Test Location",
        province="Lusaka",
        latitude=-15.4,
        longitude=28.3,
        coordinate_confidence="test-fixture",
        evidence_note="Fixture data for tests, not a real evidence claim.",
        evidence_source_url="",
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def register_and_login(client: TestClient, email: str, password: str = "testpassword123") -> str:
    """Helper: registers a real user (CITIZEN role) and returns a real access token."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def promote_to_role(db: Session, email: str, role: Role) -> None:
    from app.models.user import User

    user = db.query(User).filter_by(email=email).one()
    user.role_id = role.id
    db.commit()
