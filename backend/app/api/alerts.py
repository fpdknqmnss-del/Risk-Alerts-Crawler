from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.alert import Alert, AlertCategory
from app.models.user import User
from app.schemas.alerts import (
    AlertListResponse,
    AlertResponse,
    AlertsStatsResponse,
    AlertSortBy,
    CategoryDistributionItem,
    SeverityDistributionItem,
    SortOrder,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _apply_filters(
    query: Select,
    *,
    category: AlertCategory | None = None,
    severity_min: int | None = None,
    severity_max: int | None = None,
    country: str | None = None,
    region: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = None,
) -> Select:
    if category is not None:
        query = query.where(Alert.category == category)

    if severity_min is not None:
        query = query.where(Alert.severity >= severity_min)

    if severity_max is not None:
        query = query.where(Alert.severity <= severity_max)

    if country:
        query = query.where(Alert.country.ilike(country.strip()))

    if region:
        query = query.where(Alert.region.ilike(f"%{region.strip()}%"))

    if start_date is not None:
        query = query.where(Alert.created_at >= start_date)

    if end_date is not None:
        query = query.where(Alert.created_at <= end_date)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Alert.title.ilike(search_term),
                Alert.summary.ilike(search_term),
            )
        )

    return query


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    category: AlertCategory | None = None,
    severity_min: int | None = Query(default=None, ge=1, le=5),
    severity_max: int | None = Query(default=None, ge=1, le=5),
    country: str | None = Query(default=None, min_length=2, max_length=100),
    region: str | None = Query(default=None, min_length=1, max_length=255),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=255),
    sort_by: AlertSortBy = AlertSortBy.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertListResponse:
    base_query = _apply_filters(
        select(Alert),
        category=category,
        severity_min=severity_min,
        severity_max=severity_max,
        country=country,
        region=region,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    count_query = _apply_filters(
        select(func.count(Alert.id)),
        category=category,
        severity_min=severity_min,
        severity_max=severity_max,
        country=country,
        region=region,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )

    sort_column = Alert.created_at if sort_by == AlertSortBy.CREATED_AT else Alert.severity
    order_by_clause = sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()

    offset = (page - 1) * page_size
    query = base_query.order_by(order_by_clause, Alert.id.desc()).offset(offset).limit(page_size)

    total = int(await db.scalar(count_query) or 0)
    items = (await db.scalars(query)).all()

    return AlertListResponse(
        items=[AlertResponse.model_validate(alert) for alert in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=AlertsStatsResponse)
async def get_alert_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertsStatsResponse:
    total_alerts = int(await db.scalar(select(func.count(Alert.id))) or 0)
    critical_alerts = int(
        await db.scalar(select(func.count(Alert.id)).where(Alert.severity == 5)) or 0
    )
    countries_affected = int(
        await db.scalar(select(func.count(func.distinct(Alert.country)))) or 0
    )

    severity_rows = await db.execute(
        select(Alert.severity, func.count(Alert.id))
        .group_by(Alert.severity)
        .order_by(Alert.severity.asc())
    )
    category_rows = await db.execute(
        select(Alert.category, func.count(Alert.id))
        .group_by(Alert.category)
        .order_by(Alert.category.asc())
    )

    severity_distribution = [
        SeverityDistributionItem(severity=severity, count=count)
        for severity, count in severity_rows.all()
    ]
    category_distribution = [
        CategoryDistributionItem(category=category, count=count)
        for category, count in category_rows.all()
    ]

    return AlertsStatsResponse(
        total_alerts=total_alerts,
        critical_alerts=critical_alerts,
        countries_affected=countries_affected,
        severity_distribution=severity_distribution,
        category_distribution=category_distribution,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AlertResponse:
    alert = await db.scalar(select(Alert).where(Alert.id == alert_id))
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    return AlertResponse.model_validate(alert)
