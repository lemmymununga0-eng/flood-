"""Database-level constraint tests, run against the real Postgres test database.
These verify the schema itself enforces the invariants the application relies on —
not just application-layer checks that could be bypassed by a direct DB write."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.location import Location
from app.models.user import Role, User


def test_user_email_unique_constraint(db, seeded_roles):
    db.add(User(email="dup@example.com", hashed_password="x", role_id=seeded_roles["CITIZEN"].id))
    db.commit()
    db.add(User(email="dup@example.com", hashed_password="y", role_id=seeded_roles["CITIZEN"].id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_role_name_unique_constraint(db, seeded_roles):
    db.add(Role(name="ADMIN", description="duplicate"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_citizen_report_requires_valid_user_fk(db):
    from app.models.citizen_report import CitizenReport

    db.add(CitizenReport(reporter_user_id=999999, description="orphan FK", severity="unknown"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_alert_requires_valid_location_fk(db):
    from datetime import datetime, timezone

    from app.models.alert import Alert

    db.add(
        Alert(
            title="x",
            risk_level="high",
            location_id=999999,
            message="m",
            created_at=datetime.now(timezone.utc),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_flood_event_id_unique(db):
    from datetime import date

    from app.models.flood_event import FloodEvent

    def make_event():
        return FloodEvent(
            event_id="ZM-TEST-01",
            start_date=date(2026, 1, 1),
            provinces="Lusaka",
            districts="",
            rivers="",
            source_name="Test fixture",
            source_url="https://example.org",
        )

    db.add(make_event())
    db.commit()
    db.add(make_event())
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
