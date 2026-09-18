from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.core.deps import get_current_user, require_roles
from app.core.notifications import notify_user
from app.core.pagination import Pagination, pagination_params
from app.database.session import get_db
from app.models.citizen_report import CitizenReport
from app.models.location import Location
from app.models.user import User
from app.schemas.citizen_report import CitizenReportCreate, CitizenReportModerate, CitizenReportOut

router = APIRouter(prefix="/citizen-reports", tags=["citizen-reports"])


@router.get("", response_model=list[CitizenReportOut])
def list_reports(
    db: Session = Depends(get_db),
    status: str | None = None,
    page: Pagination = Depends(pagination_params),
) -> list[CitizenReport]:
    query = select(CitizenReport).order_by(CitizenReport.submitted_at.desc())
    if status:
        query = query.where(CitizenReport.status == status)
    return db.scalars(query.limit(page.limit).offset(page.offset)).all()


@router.post("", response_model=CitizenReportOut, status_code=201)
def submit_report(
    payload: CitizenReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CitizenReport:
    if payload.location_id is not None and db.get(Location, payload.location_id) is None:
        raise HTTPException(status_code=400, detail={"error": "unknown_location", "message": "Unknown location_id"})
    report = CitizenReport(
        reporter_user_id=current_user.id,
        location_id=payload.location_id,
        description=payload.description,
        severity=payload.severity,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/moderate", response_model=CitizenReportOut)
def moderate_report(
    report_id: int,
    payload: CitizenReportModerate,
    db: Session = Depends(get_db),
    moderator: User = Depends(require_roles("ADMIN", "ANALYST", "OPERATOR")),
) -> CitizenReport:
    report = db.get(CitizenReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Citizen report not found"})
    report.status = payload.status
    report.review_note = payload.review_note
    report.reviewed_by_user_id = moderator.id
    report.reviewed_at = datetime.now(timezone.utc)
    record_audit_event(
        db,
        user_id=moderator.id,
        action="citizen_report_moderated",
        entity_type="citizen_report",
        entity_id=report.id,
        detail=f"status={payload.status}",
    )
    if report.reporter_user_id is not None:
        notify_user(
            db,
            user_id=report.reporter_user_id,
            notification_type="citizen_report_moderated",
            title=f"Your report was {payload.status}",
            message=payload.review_note,
            entity_type="citizen_report",
            entity_id=report.id,
        )
    db.commit()
    db.refresh(report)
    return report
