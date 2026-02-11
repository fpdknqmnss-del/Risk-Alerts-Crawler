from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.tasks.fetch_news import fetch_news_task

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def enqueue_news_fetch_job() -> None:
    try:
        fetch_news_task.delay()
    except Exception:
        logger.exception("Failed to enqueue scheduled news fetch task.")


def start_scheduler() -> AsyncIOScheduler | None:
    global _scheduler

    if not settings.ENABLE_NEWS_SCHEDULER:
        logger.info("News scheduler is disabled by configuration.")
        return None

    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = AsyncIOScheduler(timezone="UTC")
    interval_minutes = max(settings.NEWS_FETCH_INTERVAL_MINUTES, 1)
    scheduler.add_job(
        enqueue_news_fetch_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="news-fetch-job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "News scheduler started (interval=%s minutes).",
        interval_minutes,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("News scheduler stopped.")
    _scheduler = None
