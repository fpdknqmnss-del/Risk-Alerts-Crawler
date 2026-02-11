from celery import Celery

from app.config import settings

celery_app = Celery(
    "risk_alerts_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.fetch_news", "app.tasks.send_emails", "app.tasks.generate_report"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
