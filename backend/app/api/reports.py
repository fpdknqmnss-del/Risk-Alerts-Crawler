from __future__ import annotations

from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.report import (
    ReportCreateRequest,
    ReportGenerationRequest,
    ReportGenerationResponse,
    ReportResponse,
)
from app.services.report_generator import ReportGeneratorService
from app.tasks.generate_report import generate_report_task

router = APIRouter(prefix="/reports", tags=["reports"])
report_generator_service = ReportGeneratorService()


async def _ensure_report_table(db: AsyncSession) -> None:
    await db.run_sync(
        lambda sync_session: Report.__table__.create(
            bind=sync_session.connection(),
            checkfirst=True,
        )
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Report]:
    await _ensure_report_table(db)
    result = await db.execute(
        select(Report).order_by(Report.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Report:
    await _ensure_report_table(db)
    report = await db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Report:
    await _ensure_report_table(db)
    report = Report(
        title=payload.title.strip(),
        summary=payload.summary,
        content_json=payload.content_json,
        status=ReportStatus.DRAFT,
        created_by=current_user.id,
        geographic_scope=payload.geographic_scope,
        date_range_start=(
            None
            if payload.date_range_start is None
            else datetime.combine(payload.date_range_start, time.min, tzinfo=timezone.utc)
        ),
        date_range_end=(
            None
            if payload.date_range_end is None
            else datetime.combine(payload.date_range_end, time.max, tzinfo=timezone.utc)
        ),
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


@router.post("/{report_id}/submit", response_model=ReportResponse)
async def submit_for_approval(
    report_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Report:
    await _ensure_report_table(db)
    report = await db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status != ReportStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only draft reports can be submitted (current: {report.status.value})",
        )

    report.status = ReportStatus.PENDING_APPROVAL
    await db.flush()
    await db.refresh(report)
    return report


@router.post(
    "/generate",
    response_model=ReportGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    payload: ReportGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportGenerationResponse:
    try:
        result = await report_generator_service.generate_report(
            db=db,
            created_by=current_user.id,
            payload=payload,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {error}",
        ) from error

    return ReportGenerationResponse(report=result.report, alerts_used=result.alerts_used)


@router.post(
    "/generate-async",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_report_async(
    payload: ReportGenerationRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Queue report generation as a background task. Returns a task ID for polling."""
    task = generate_report_task.delay(
        created_by=current_user.id,
        payload_dict=payload.model_dump(mode="json"),
    )
    return {"task_id": task.id, "status": "queued"}


@router.get("/{report_id}/pdf")
async def download_report_pdf(
    report_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    await _ensure_report_table(db)
    report = await db.scalar(select(Report).where(Report.id == report_id))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not report.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No PDF generated for this report",
        )

    output_path = report_generator_service.output_directory / report.pdf_path
    if not output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report PDF file not found",
        )

    return FileResponse(
        path=str(output_path),
        media_type="application/pdf",
        filename=report.pdf_path,
    )
