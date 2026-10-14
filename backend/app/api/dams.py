"""Dam and reservoir monitoring. Entirely separate from the flood-prediction model:
nothing here imports app.ml, and nothing here writes predictions or alerts."""
import datetime as dt

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database.session import get_db
from app.models.dam import Dam, DamObservation, DamReleaseNotice
from app.models.user import User
from app.services.dam_assessment import assess
from app.services.dam_validation import DATA_KINDS, MEASUREMENTS, freshness, parse_csv

router = APIRouter(prefix="/dams", tags=["dams"])

_MAX_CSV_BYTES = 2_000_000


def _iso(t: dt.datetime | None) -> str | None:
    return t.isoformat() if t else None


def _utc(t: dt.datetime) -> dt.datetime:
    return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc)


def _get_dam(db: Session, slug: str) -> Dam:
    dam = db.scalar(select(Dam).where(Dam.slug == slug))
    if dam is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Dam not found"})
    return dam


def _latest(db: Session, dam_id: int) -> DamObservation | None:
    return db.scalars(
        select(DamObservation).where(DamObservation.dam_id == dam_id)
        .order_by(DamObservation.observed_at.desc()).limit(1)
    ).first()


def _obs_out(o: DamObservation) -> dict:
    return {
        "observed_at": _iso(o.observed_at), "source_published_at": _iso(o.source_published_at),
        "retrieved_at": _iso(o.retrieved_at), "data_kind": o.data_kind, "provider": o.provider,
        "source_reference": o.source_reference, "quality_flag": o.quality_flag,
        **{m: getattr(o, m) for m in MEASUREMENTS},   # None stays None
    }


def _dam_out(dam: Dam, latest: DamObservation | None) -> dict:
    return {
        "slug": dam.slug, "name": dam.name, "river_system": dam.river_system, "district": dam.district,
        "province": dam.province, "latitude": dam.latitude, "longitude": dam.longitude,
        "coordinate_source": dam.coordinate_source, "capacity_m3": dam.capacity_m3,
        "capacity_source": dam.capacity_source, "data_provider": dam.data_provider,
        "data_status": dam.data_status, "last_successful_update": _iso(dam.last_successful_update),
        "notes": dam.notes, "verification_required": dam.verification_required,
        "freshness": freshness(latest.observed_at if latest else None),
        "latest": _obs_out(latest) if latest else None,
    }


@router.get("")
def list_dams(db: Session = Depends(get_db)) -> list[dict]:
    dams = db.scalars(select(Dam).order_by(Dam.name)).all()
    return [_dam_out(d, _latest(db, d.id)) for d in dams]


@router.get("/{slug}")
def dam_detail(
    slug: str,
    since: dt.datetime | None = Query(default=None, description="ISO 8601 with offset"),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    dam = _get_dam(db, slug)
    q = select(DamObservation).where(DamObservation.dam_id == dam.id)
    if since is not None:
        q = q.where(DamObservation.observed_at >= since)
    rows = list(reversed(db.scalars(q.order_by(DamObservation.observed_at.desc()).limit(limit)).all()))
    notices = db.scalars(
        select(DamReleaseNotice).where(DamReleaseNotice.dam_id == dam.id)
        .order_by(DamReleaseNotice.published_at.desc())
    ).all()
    return {
        "dam": _dam_out(dam, rows[-1] if rows else None),
        "observations": [_obs_out(o) for o in rows],
        "release_notices": [
            {"published_at": _iso(n.published_at), "effective_from": _iso(n.effective_from),
             "effective_to": _iso(n.effective_to), "description": n.description,
             "source_reference": n.source_reference, "issuing_body": n.issuing_body}
            for n in notices
        ],
        "units": {k: v[0] for k, v in MEASUREMENTS.items()},
    }


@router.get("/{slug}/assessment")
def dam_assessment(slug: str, db: Session = Depends(get_db)) -> dict:
    """Experimental, rule-based, read-only. Never creates alerts."""
    dam = _get_dam(db, slug)
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=5 * 365)
    obs = db.scalars(select(DamObservation).where(
        DamObservation.dam_id == dam.id, DamObservation.observed_at >= since)).all()
    notices = db.scalars(select(DamReleaseNotice).where(DamReleaseNotice.dam_id == dam.id)).all()
    return assess(list(obs), list(notices))


@router.post("/{slug}/import")
def import_observations(
    slug: str,
    data_kind: str = Query(..., description="historical | manual_import | synthetic_test"),
    csv_text: str = Body(..., media_type="text/csv"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ANALYST")),
) -> dict:
    """Validated CSV import. 'live' is refused: no live feed is operational. All-or-nothing:
    if any row is invalid nothing is stored. Existing rows are never overwritten."""
    if data_kind not in DATA_KINDS or data_kind == "live":
        raise HTTPException(status_code=422, detail={
            "error": "invalid_data_kind",
            "message": "data_kind must be historical, manual_import or synthetic_test."})
    if len(csv_text.encode()) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail={"error": "too_large", "message": "CSV exceeds 2 MB."})
    dam = _get_dam(db, slug)
    parsed = parse_csv(csv_text)
    if parsed.errors or not parsed.rows:
        raise HTTPException(status_code=422, detail={
            "error": "invalid_csv", "message": "Import rejected; nothing was stored.",
            "errors": parsed.errors[:50]})

    existing = {(_utc(o.observed_at), o.provider) for o in db.scalars(
        select(DamObservation).where(DamObservation.dam_id == dam.id))}
    now = dt.datetime.now(dt.timezone.utc)
    added = skipped = 0
    for row in parsed.rows:
        if (row["observed_at"], row["provider"]) in existing:
            skipped += 1
            continue
        db.add(DamObservation(
            dam_id=dam.id, observed_at=row["observed_at"], source_published_at=row["source_published_at"],
            retrieved_at=now, data_kind=data_kind, provider=row["provider"],
            source_reference=row["source_reference"], quality_flag=row["quality_flag"],
            **row["measurements"]))
        added += 1
    if added and data_kind != "synthetic_test":
        dam.last_successful_update = now
        dam.data_status = "historical_only" if data_kind == "historical" else "manual_import"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": "Duplicate rows."})
    return {"added": added, "skipped_existing": skipped, "data_kind": data_kind}
