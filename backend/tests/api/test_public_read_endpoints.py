"""API tests for the pre-existing public read endpoints, re-verified against the
expanded backend to guard against regression."""
from datetime import date

from app.models.flood_event import FloodEvent


def test_locations_endpoint_returns_seeded_location(client, seeded_location):
    resp = client.get("/api/v1/locations")
    assert resp.status_code == 200
    names = [loc["name"] for loc in resp.json()]
    assert "Test Location" in names


def test_locations_filter_by_province(client, seeded_location):
    resp = client.get("/api/v1/locations?province=Lusaka")
    assert resp.status_code == 200
    assert all(loc["province"] == "Lusaka" for loc in resp.json())

    resp_empty = client.get("/api/v1/locations?province=NoSuchProvince")
    assert resp_empty.json() == []


def test_locations_pagination_limit(client, db):
    from app.models.location import Location

    for i in range(5):
        db.add(
            Location(
                name=f"Loc {i}",
                province="Lusaka",
                latitude=-15.0,
                longitude=28.0,
                coordinate_confidence="test",
            )
        )
    db.commit()
    resp = client.get("/api/v1/locations?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_flood_events_endpoint_honest_when_empty(client):
    resp = client.get("/api/v1/flood-events")
    assert resp.status_code == 200
    assert resp.json() == []


def test_flood_events_returns_real_rows(client, db):
    db.add(
        FloodEvent(
            event_id="ZM-TEST-99",
            start_date=date(2024, 1, 1),
            provinces="Southern",
            districts="",
            rivers="",
            source_name="Test",
            source_url="https://example.org",
        )
    )
    db.commit()
    resp = client.get("/api/v1/flood-events")
    assert resp.status_code == 200
    assert any(e["event_id"] == "ZM-TEST-99" for e in resp.json())


def test_predictions_legitimately_empty(client):
    resp = client.get("/api/v1/predictions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_model_registry_legitimately_empty(client):
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    assert resp.json() == []


def test_model_registry_unknown_id_is_404(client):
    resp = client.get("/api/v1/models/999999")
    assert resp.status_code == 404


def test_system_status_reports_real_components(client):
    resp = client.get("/api/v1/system-status")
    assert resp.status_code == 200
    body = resp.json()
    assert "components" in body
    names = [c["name"] for c in body["components"]]
    assert "Database" in names or any("Database" in n for n in names)


def test_data_sources_catalog_is_seeded_separately_not_hardcoded(client):
    # No data sources are seeded by the test fixtures — this project only ever
    # populates data_sources via scripts/seed_db.py, so an empty catalog here is the
    # honest result, not a bug.
    resp = client.get("/api/v1/data-sources")
    assert resp.status_code == 200
    assert resp.json() == []
