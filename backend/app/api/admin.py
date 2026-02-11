from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_roles
from app.models.report import Report, ReportStatus
from app.models.user import User, UserRole
from app.schemas.report import (
    ReportApprovalRequest,
    ReportDispatchRequest,
    ReportDispatchResponse,
    ReportResponse,
)
from app.tasks.send_emails import send_report_to_mailing_lists_task

router = APIRouter(prefix="/admin", tags=["admin"])


async def _ensure_report_table(db: AsyncSession) -> None:
    await db.run_sync(
        lambda sync_session: Report.__table__.create(
            bind=sync_session.connection(),
            checkfirst=True,
        )
    )


@router.get("/reports/pending", response_model=list[ReportResponse])
async def list_pending_reports(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[Report]:
    await _ensure_report_table(db)
    pending_reports = (
        await db.scalars(
            select(Report)
            .where(Report.status == ReportStatus.PENDING_APPROVAL)
            .order_by(Report.created_at.desc())
        )
    ).all()
    return list(pending_reports)


@router.post("/reports/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    report_id: int,
    payload: ReportApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> Report:
    await _ensure_report_table(db)
    report = await db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status not in (ReportStatus.PENDING_APPROVAL, ReportStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot approve report in status '{report.status.value}'",
        )

    report.status = ReportStatus.APPROVED
    report.approved_by = current_admin.id
    payload_data = report.content_json or {}
    payload_data["approval"] = {
        "approved_by": current_admin.id,
        "comment": payload.comment,
    }
    report.content_json = payload_data
    await db.flush()
    await db.refresh(report)
    return report


@router.post("/reports/{report_id}/reject", response_model=ReportResponse)
async def reject_report(
    report_id: int,
    payload: ReportApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> Report:
    await _ensure_report_table(db)
    report = await db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status not in (ReportStatus.PENDING_APPROVAL, ReportStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject report in status '{report.status.value}'",
        )

    report.status = ReportStatus.DRAFT
    report.approved_by = current_admin.id
    payload_data = report.content_json or {}
    payload_data["rejection"] = {
        "reviewed_by": current_admin.id,
        "comment": payload.comment,
    }
    report.content_json = payload_data
    await db.flush()
    await db.refresh(report)
    return report


@router.post("/reports/{report_id}/dispatch", response_model=ReportDispatchResponse)
async def dispatch_report(
    report_id: int,
    payload: ReportDispatchRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> ReportDispatchResponse:
    await _ensure_report_table(db)
    report = await db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status != ReportStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved reports can be dispatched",
        )

    task = send_report_to_mailing_lists_task.delay(
        report_id=report.id,
        mailing_list_ids=payload.mailing_list_ids or None,
        use_geographic_match=payload.use_geographic_match,
    )
    return ReportDispatchResponse(task_id=task.id, status="queued")
