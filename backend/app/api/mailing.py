from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.mailing_list import MailingList
from app.models.subscriber import Subscriber
from app.models.user import User, UserRole
from app.schemas.mailing import (
    CsvImportResponse,
    MailingListCreateRequest,
    MailingListResponse,
    MailingListUpdateRequest,
    SubscriberCreateRequest,
    SubscriberResponse,
)

router = APIRouter(prefix="/mailing", tags=["mailing"])


async def _ensure_tables(db: AsyncSession) -> None:
    await db.run_sync(
        lambda sync_session: MailingList.__table__.create(
            bind=sync_session.connection(),
            checkfirst=True,
        )
    )
    await db.run_sync(
        lambda sync_session: Subscriber.__table__.create(
            bind=sync_session.connection(),
            checkfirst=True,
        )
    )


def _subscriber_count_query() -> Select:
    subscriber_counts = (
        select(
            Subscriber.mailing_list_id.label("mailing_list_id"),
            func.count(Subscriber.id).label("subscriber_count"),
        )
        .group_by(Subscriber.mailing_list_id)
        .subquery()
    )
    return (
        select(
            MailingList,
            func.coalesce(subscriber_counts.c.subscriber_count, 0).label("subscriber_count"),
        )
        .outerjoin(subscriber_counts, subscriber_counts.c.mailing_list_id == MailingList.id)
        .order_by(MailingList.created_at.desc())
    )


@router.get("/lists", response_model=list[MailingListResponse])
async def list_mailing_lists(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MailingListResponse]:
    await _ensure_tables(db)
    rows = (await db.execute(_subscriber_count_query())).all()
    return [
        MailingListResponse(
            id=mailing_list.id,
            name=mailing_list.name,
            geographic_regions=mailing_list.geographic_regions or [],
            description=mailing_list.description,
            created_by=mailing_list.created_by,
            created_at=mailing_list.created_at,
            subscriber_count=int(subscriber_count or 0),
        )
        for mailing_list, subscriber_count in rows
    ]


@router.post("/lists", response_model=MailingListResponse, status_code=status.HTTP_201_CREATED)
async def create_mailing_list(
    payload: MailingListCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> MailingListResponse:
    await _ensure_tables(db)
    existing = await db.scalar(
        select(MailingList).where(MailingList.name == payload.name.strip())
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A mailing list with this name already exists",
        )

    mailing_list = MailingList(
        name=payload.name.strip(),
        geographic_regions=[region.strip() for region in payload.geographic_regions if region.strip()],
        description=(payload.description.strip() if payload.description else None),
        created_by=current_admin.id,
    )
    db.add(mailing_list)
    await db.flush()
    await db.refresh(mailing_list)
    return MailingListResponse(
        id=mailing_list.id,
        name=mailing_list.name,
        geographic_regions=mailing_list.geographic_regions or [],
        description=mailing_list.description,
        created_by=mailing_list.created_by,
        created_at=mailing_list.created_at,
        subscriber_count=0,
    )


@router.put("/lists/{mailing_list_id}", response_model=MailingListResponse)
async def update_mailing_list(
    mailing_list_id: int,
    payload: MailingListUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> MailingListResponse:
    await _ensure_tables(db)
    mailing_list = await db.scalar(select(MailingList).where(MailingList.id == mailing_list_id))
    if mailing_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailing list not found")

    duplicate = await db.scalar(
        select(MailingList).where(
            MailingList.name == payload.name.strip(),
            MailingList.id != mailing_list_id,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A mailing list with this name already exists",
        )

    mailing_list.name = payload.name.strip()
    mailing_list.geographic_regions = [
        region.strip() for region in payload.geographic_regions if region.strip()
    ]
    mailing_list.description = payload.description.strip() if payload.description else None
    await db.flush()

    subscriber_count = int(
        await db.scalar(
            select(func.count(Subscriber.id)).where(Subscriber.mailing_list_id == mailing_list.id)
        )
        or 0
    )
    return MailingListResponse(
        id=mailing_list.id,
        name=mailing_list.name,
        geographic_regions=mailing_list.geographic_regions or [],
        description=mailing_list.description,
        created_by=mailing_list.created_by,
        created_at=mailing_list.created_at,
        subscriber_count=subscriber_count,
    )


@router.delete("/lists/{mailing_list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mailing_list(
    mailing_list_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    await _ensure_tables(db)
    mailing_list = await db.scalar(select(MailingList).where(MailingList.id == mailing_list_id))
    if mailing_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailing list not found")
    await db.delete(mailing_list)


@router.get("/lists/{mailing_list_id}/subscribers", response_model=list[SubscriberResponse])
async def list_subscribers(
    mailing_list_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Subscriber]:
    await _ensure_tables(db)
    mailing_list = await db.scalar(select(MailingList).where(MailingList.id == mailing_list_id))
    if mailing_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailing list not found")

    subscribers = (
        await db.scalars(
            select(Subscriber)
            .where(Subscriber.mailing_list_id == mailing_list_id)
            .order_by(Subscriber.created_at.desc())
        )
    ).all()
    return list(subscribers)


@router.post(
    "/lists/{mailing_list_id}/subscribers",
    response_model=SubscriberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscriber(
    mailing_list_id: int,
    payload: SubscriberCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> Subscriber:
    await _ensure_tables(db)
    mailing_list = await db.scalar(select(MailingList).where(MailingList.id == mailing_list_id))
    if mailing_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailing list not found")

    normalized_email = payload.email.strip().lower()
    existing = await db.scalar(
        select(Subscriber).where(
            Subscriber.mailing_list_id == mailing_list_id,
            Subscriber.email == normalized_email,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subscriber email already exists in this mailing list",
        )

    subscriber = Subscriber(
        email=normalized_email,
        name=payload.name.strip() if payload.name else None,
        organization=payload.organization.strip() if payload.organization else None,
        mailing_list_id=mailing_list_id,
    )
    db.add(subscriber)
    await db.flush()
    await db.refresh(subscriber)
    return subscriber


@router.delete("/lists/{mailing_list_id}/subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscriber(
    mailing_list_id: int,
    subscriber_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    await _ensure_tables(db)
    subscriber = await db.scalar(
        select(Subscriber).where(
            Subscriber.id == subscriber_id,
            Subscriber.mailing_list_id == mailing_list_id,
        )
    )
    if subscriber is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscriber not found")
    await db.delete(subscriber)


@router.post(
    "/lists/{mailing_list_id}/subscribers/import-csv",
    response_model=CsvImportResponse,
)
async def import_subscribers_csv(
    mailing_list_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> CsvImportResponse:
    await _ensure_tables(db)
    mailing_list = await db.scalar(select(MailingList).where(MailingList.id == mailing_list_id))
    if mailing_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailing list not found")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported",
        )

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file must be UTF-8 encoded",
        ) from error

    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)
    if reader.fieldnames is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV is missing a header row",
        )

    total_rows = len(rows)
    imported_count = 0
    skipped_count = 0
    invalid_rows = 0

    for row in rows:
        raw_email = (row.get("email") or "").strip().lower()
        if not raw_email:
            invalid_rows += 1
            continue

        duplicate = await db.scalar(
            select(Subscriber).where(
                Subscriber.mailing_list_id == mailing_list_id,
                Subscriber.email == raw_email,
            )
        )
        if duplicate is not None:
            skipped_count += 1
            continue

        subscriber = Subscriber(
            email=raw_email,
            name=((row.get("name") or "").strip() or None),
            organization=((row.get("organization") or "").strip() or None),
            mailing_list_id=mailing_list_id,
        )
        db.add(subscriber)
        imported_count += 1

    return CsvImportResponse(
        total_rows=total_rows,
        imported_count=imported_count,
        skipped_count=skipped_count,
        invalid_rows=invalid_rows,
    )
