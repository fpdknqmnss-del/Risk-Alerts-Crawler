from __future__ import annotations

import asyncio

from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.services.news_aggregator import NewsAggregatorService

logger = get_task_logger(__name__)


async def _run_fetch(limit_per_source: int) -> dict:
    service = NewsAggregatorService()
    return await service.fetch_and_store(limit_per_source=limit_per_source)


@celery_app.task(
    bind=True,
    name="news.fetch_latest",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def fetch_news_task(self, limit_per_source: int = 50) -> dict:  # noqa: ANN001
    logger.info("Starting news fetch task with limit_per_source=%s", limit_per_source)
    result = asyncio.run(_run_fetch(limit_per_source=limit_per_source))
    logger.info("News fetch task completed: %s", result)
    return result
