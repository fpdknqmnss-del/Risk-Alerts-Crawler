from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import datetime, timezone
from typing import Sequence

import feedparser
import httpx

from app.config import settings
from app.sources.base import (
    NewsSourceAdapter,
    NormalizedNewsItem,
    make_json_serializable,
    normalize_datetime,
)

logger = logging.getLogger(__name__)


class RSSFeedsAdapter(NewsSourceAdapter):
    source_name = "rss"

    def __init__(
        self,
        feed_urls: Sequence[str] | None = None,
        request_timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(request_timeout_seconds=request_timeout_seconds)
        self.feed_urls = list(feed_urls or settings.rss_feed_urls_list)

    async def fetch_recent(self, limit: int = 50) -> list[NormalizedNewsItem]:
        if not self.feed_urls:
            return []

        async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
            parsed_results = await asyncio.gather(
                *(self._fetch_and_parse_feed(client, feed_url) for feed_url in self.feed_urls),
                return_exceptions=True,
            )

        normalized: list[NormalizedNewsItem] = []
        for feed_url, parsed in zip(self.feed_urls, parsed_results):
            if isinstance(parsed, Exception):
                logger.warning("Failed to parse RSS feed %s: %s", feed_url, parsed)
                continue

            feed_title = parsed.feed.get("title", self.source_name)
            for entry in parsed.entries:
                title = entry.get("title")
                url = entry.get("link")
                if not title or not url:
                    continue

                normalized.append(
                    NormalizedNewsItem(
                        source=feed_title,
                        title=title,
                        url=url,
                        description=entry.get("summary"),
                        content=entry.get("content", [{}])[0].get("value")
                        if entry.get("content")
                        else None,
                        published_at=self._extract_published_at(entry),
                        country=None,
                        region=None,
                        latitude=None,
                        longitude=None,
                        payload=make_json_serializable({"feed_url": feed_url, "entry": dict(entry)}),
                    )
                )

        normalized.sort(
            key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return normalized[:limit]

    async def _fetch_and_parse_feed(self, client: httpx.AsyncClient, feed_url: str):
        response = await client.get(feed_url, follow_redirects=True)
        response.raise_for_status()
        return feedparser.parse(response.text)

    def _extract_published_at(self, entry: dict) -> datetime | None:
        published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if published_struct is not None:
            return datetime.fromtimestamp(calendar.timegm(published_struct), tz=timezone.utc)

        return normalize_datetime(entry.get("published") or entry.get("updated"))
