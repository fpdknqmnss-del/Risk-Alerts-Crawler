from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session
from app.models.mailing_list import MailingList
from app.models.report import Report, ReportStatus
from app.models.subscriber import Subscriber
from app.services.email_service import EmailService

logger = get_task_logger(__name__)


def _normalize_region_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    separator_normalized = (
        value.replace("|", ",")
        .replace("/", ",")
        .replace(";", ",")
        .replace("\n", ",")
        .replace("\t", ",")
    )
    return {token.strip().lower() for token in separator_normalized.split(",") if token.strip()}


def _mailing_list_matches_scope(
    mailing_list: MailingList,
    report_scope_tokens: set[str],
) -> bool:
    if not report_scope_tokens:
        return True

    list_regions = mailing_list.geographic_regions or []
    list_tokens: set[str] = set()
    for region in list_regions:
        if isinstance(region, str):
            list_tokens.update(_normalize_region_tokens(region))

    if not list_tokens:
        return False
    return bool(report_scope_tokens & list_tokens)


async def _dispatch_report_email(
    report_id: int,
    mailing_list_ids: list[int] | None = None,
    use_geographic_match: bool = True,
) -> dict[str, Any]:
    async with async_session() as db:
        report = await db.scalar(select(Report).where(Report.id == report_id))
        if report is None:
            raise ValueError(f"Report {report_id} not found")
        if report.status != ReportStatus.APPROVED:
            raise ValueError("Only approved reports can be sent")

        all_lists = (await db.scalars(select(MailingList))).all()
        selected_lists: list[MailingList] = []
        if mailing_list_ids:
            allowed_ids = set(mailing_list_ids)
            selected_lists = [mailing_list for mailing_list in all_lists if mailing_list.id in allowed_ids]
        elif use_geographic_match:
            scope_tokens = _normalize_region_tokens(report.geographic_scope)
            selected_lists = [
                mailing_list
                for mailing_list in all_lists
                if _mailing_list_matches_scope(mailing_list, scope_tokens)
            ]

        if not selected_lists:
            delivery_data = {
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "mailing_lists": [],
                "sent_count": 0,
                "failed_count": 0,
                "status": "no_targets",
            }
            payload = report.content_json or {}
            payload["delivery"] = delivery_data
            report.content_json = payload
            await db.commit()
            return delivery_data

        selected_list_ids = [mailing_list.id for mailing_list in selected_lists]
        subscribers = (
            await db.scalars(
                select(Subscriber).where(Subscriber.mailing_list_id.in_(selected_list_ids))
            )
        ).all()

        unique_subscribers: dict[str, Subscriber] = {}
        for subscriber in subscribers:
            key = subscriber.email.strip().lower()
            if key:
                unique_subscribers[key] = subscriber

        email_service = EmailService()
        sent_count = 0
        failed_count = 0
        failures: list[dict[str, str]] = []

        for subscriber in unique_subscribers.values():
            try:
                email_service.send_report_email(
                    recipient_email=subscriber.email,
                    report_title=report.title,
                    report_summary=report.summary,
                    report_pdf_url=report.pdf_path,
                )
                sent_count += 1
            except Exception as error:
                failed_count += 1
                failures.append({"email": subscriber.email, "error": str(error)})
                logger.exception("Failed sending report email to %s", subscriber.email)

        report.status = ReportStatus.SENT
        payload = report.content_json or {}
        payload["delivery"] = {
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "mailing_lists": selected_list_ids,
            "recipient_count": len(unique_subscribers),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "failures": failures[:50],
            "status": "completed",
        }
        report.content_json = payload
        await db.commit()

        return payload["delivery"]


@celery_app.task(
    bind=True,
    name="reports.send_to_mailing_lists",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def send_report_to_mailing_lists_task(  # noqa: ANN001
    self,
    report_id: int,
    mailing_list_ids: list[int] | None = None,
    use_geographic_match: bool = True,
) -> dict[str, Any]:
    logger.info(
        "Sending report %s to mailing lists (ids=%s, use_geographic_match=%s)",
        report_id,
        mailing_list_ids,
        use_geographic_match,
    )
    result = asyncio.run(
        _dispatch_report_email(
            report_id=report_id,
            mailing_list_ids=mailing_list_ids,
            use_geographic_match=use_geographic_match,
        )
    )
    logger.info("Report %s email dispatch completed: %s", report_id, result)
    return result
