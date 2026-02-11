from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.agents import (
    ClassificationAgent,
    DeduplicationService,
    LLMProviderFactory,
    SeverityScorerAgent,
    SummarizationAgent,
    VerificationAgent,
)
from app.config import settings
from app.database import async_session
from app.models.alert import Alert
from app.models.raw_news_item import RawNewsItem
from app.sources import (
    GDELTAdapter,
    NewsAPIAdapter,
    NewsSourceAdapter,
    NormalizedNewsItem,
    RSSFeedsAdapter,
    ReliefWebAdapter,
    USGSAdapter,
)

logger = logging.getLogger(__name__)


class NewsAggregatorService:
    def __init__(self, adapters: list[NewsSourceAdapter] | None = None) -> None:
        self.adapters = adapters or self._build_default_adapters()
        llm_factory = LLMProviderFactory()
        self.verification_agent = VerificationAgent(llm_factory=llm_factory)
        self.classification_agent = ClassificationAgent(llm_factory=llm_factory)
        self.severity_scorer = SeverityScorerAgent(llm_factory=llm_factory)
        self.summarization_agent = SummarizationAgent(llm_factory=llm_factory)

    def _build_default_adapters(self) -> list[NewsSourceAdapter]:
        timeout = settings.REQUEST_TIMEOUT_SECONDS
        return [
            NewsAPIAdapter(request_timeout_seconds=timeout),
            GDELTAdapter(request_timeout_seconds=timeout),
            RSSFeedsAdapter(request_timeout_seconds=timeout),
            ReliefWebAdapter(request_timeout_seconds=timeout),
            USGSAdapter(request_timeout_seconds=timeout),
        ]

    async def fetch_all_sources(self, limit_per_source: int = 50) -> list[NormalizedNewsItem]:
        results: list[NormalizedNewsItem] = []
        fetch_results = await asyncio.gather(
            *(adapter.fetch_recent(limit=limit_per_source) for adapter in self.adapters),
            return_exceptions=True,
        )

        for adapter, fetched_result in zip(self.adapters, fetch_results):
            if isinstance(fetched_result, Exception):
                logger.error(
                    "Failed to fetch source '%s': %s",
                    adapter.source_name,
                    fetched_result,
                )
                continue

            fetched_items = fetched_result
            try:
                logger.info(
                    "Fetched %s items from source '%s'.",
                    len(fetched_items),
                    adapter.source_name,
                )
                results.extend(fetched_items)
            except Exception:
                logger.exception("Failed to normalize source '%s'.", adapter.source_name)

        return self._deduplicate(results)

    async def store_raw_items(
        self,
        db: AsyncSession,
        items: list[NormalizedNewsItem],
    ) -> int:
        if not items:
            return 0

        values = [
            {
                "source": item.source,
                "title": item.title[:500],
                "url": item.url[:1024],
                "description": item.description,
                "content": item.content,
                "published_at": item.published_at,
                "country": item.country,
                "region": item.region,
                "latitude": item.latitude,
                "longitude": item.longitude,
                "payload": item.payload,
            }
            for item in items
            if item.title and item.url
        ]

        if not values:
            return 0

        statement = pg_insert(RawNewsItem).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=[RawNewsItem.source, RawNewsItem.url],
            set_={
                "title": statement.excluded.title,
                "description": statement.excluded.description,
                "content": statement.excluded.content,
                "published_at": statement.excluded.published_at,
                "country": statement.excluded.country,
                "region": statement.excluded.region,
                "latitude": statement.excluded.latitude,
                "longitude": statement.excluded.longitude,
                "payload": statement.excluded.payload,
                "fetched_at": func.now(),
            },
        )
        await db.execute(statement)
        return len(values)

    async def fetch_and_store(self, limit_per_source: int = 50) -> dict:
        fetched_items = await self.fetch_all_sources(limit_per_source=limit_per_source)
        if not fetched_items:
            return {
                "fetched_count": 0,
                "stored_count": 0,
                "created_alerts_count": 0,
                "skipped_duplicates_count": 0,
                "source_counts": {},
            }

        async with async_session() as db:
            try:
                await self._ensure_raw_news_table(db)
                await self._ensure_alert_table(db)
                stored_count = await self.store_raw_items(db, fetched_items)
                alert_metrics = await self.create_alerts_from_items(db, fetched_items)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

        source_counts = dict(Counter(item.source for item in fetched_items))
        return {
            "fetched_count": len(fetched_items),
            "stored_count": stored_count,
            "created_alerts_count": alert_metrics["created_alerts_count"],
            "skipped_duplicates_count": alert_metrics["skipped_duplicates_count"],
            "source_counts": source_counts,
        }

    async def _ensure_raw_news_table(self, db: AsyncSession) -> None:
        await db.run_sync(
            lambda sync_session: RawNewsItem.__table__.create(
                bind=sync_session.connection(),
                checkfirst=True,
            )
        )

    async def _ensure_alert_table(self, db: AsyncSession) -> None:
        await db.run_sync(
            lambda sync_session: Alert.__table__.create(
                bind=sync_session.connection(),
                checkfirst=True,
            )
        )

    async def create_alerts_from_items(
        self,
        db: AsyncSession,
        items: list[NormalizedNewsItem],
    ) -> dict[str, int]:
        if not items:
            return {"created_alerts_count": 0, "skipped_duplicates_count": 0}

        deduper = DeduplicationService(
            similarity_threshold=settings.DEDUP_SIMILARITY_THRESHOLD,
            embedding_dimensions=settings.DEDUP_EMBEDDING_DIMENSIONS,
        )
        recent_alert_texts = await self._load_recent_alert_texts(db)
        deduper.index_existing_alert_texts(recent_alert_texts)

        alerts: list[Alert] = []
        skipped_duplicates_count = 0

        for item in items:
            similarity = deduper.is_duplicate_news_item(item)
            if similarity.is_duplicate:
                skipped_duplicates_count += 1
                continue

            verification = await self.verification_agent.verify(item)
            classification = await self.classification_agent.classify(item)
            severity = await self.severity_scorer.score(item, classification, verification)
            summary = await self.summarization_agent.summarize(
                item,
                classification,
                severity,
                verification,
            )

            country = (classification.country or item.country or "Unknown").strip()[:100]
            region_value = classification.region or item.region
            region = region_value.strip()[:255] if isinstance(region_value, str) and region_value.strip() else None
            full_content = (item.content or item.description or item.title).strip()

            alert = Alert(
                title=item.title[:500],
                summary=summary,
                full_content=full_content,
                category=classification.category,
                severity=severity.severity,
                country=country,
                region=region,
                latitude=item.latitude,
                longitude=item.longitude,
                sources=self._build_sources_payload(item),
                verified=verification.verified,
                verification_score=round(verification.verification_score, 4),
            )
            alerts.append(alert)
            deduper.register_news_item(item, summary=summary)

        if alerts:
            db.add_all(alerts)
            await db.flush()

        return {
            "created_alerts_count": len(alerts),
            "skipped_duplicates_count": skipped_duplicates_count,
        }

    async def _load_recent_alert_texts(self, db: AsyncSession) -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.DEDUP_ALERT_LOOKBACK_HOURS)
        result = await db.execute(
            select(Alert.title, Alert.summary, Alert.full_content).where(Alert.created_at >= cutoff)
        )
        rows = result.all()
        return [
            " ".join(part for part in [title, summary, full_content] if part)
            for title, summary, full_content in rows
        ]

    def _build_sources_payload(self, item: NormalizedNewsItem) -> list[dict[str, str | None]]:
        return [
            {
                "source": item.source,
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
            }
        ]

    def _deduplicate(self, items: list[NormalizedNewsItem]) -> list[NormalizedNewsItem]:
        seen_keys: set[tuple[str, str]] = set()
        deduplicated: list[NormalizedNewsItem] = []

        for item in items:
            key = (item.source.lower().strip(), item.url.lower().strip())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduplicated.append(item)

        return deduplicated
