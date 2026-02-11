from __future__ import annotations

import asyncio

from celery.utils.log import get_task_logger

from app.celery_app import celery_app

logger = get_task_logger(__name__)


async def _run_generate(created_by: int, payload_dict: dict) -> dict:
    from app.database import async_session
    from app.schemas.report import ReportGenerationRequest
    from app.services.report_generator import ReportGeneratorService

    payload = ReportGenerationRequest(**payload_dict)
    service = ReportGeneratorService()

    async with async_session() as db:
        try:
            result = await service.generate_report(
                db=db,
                created_by=created_by,
                payload=payload,
            )
            await db.commit()
            return {"report_id": result.report.id, "alerts_used": result.alerts_used}
        except Exception as e:
            logger.exception("Report generation failed: %s", e)
            raise


@celery_app.task(
    bind=True,
    name="reports.generate",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def generate_report_task(self, created_by: int, payload_dict: dict) -> dict:
    logger.info("Starting report generation task for user %s", created_by)
    try:
        result = asyncio.run(_run_generate(created_by=created_by, payload_dict=payload_dict))
        logger.info("Report generation completed: %s", result)
        return result
    except Exception as e:
        logger.exception("Report generation task failed: %s", e)
        raise
