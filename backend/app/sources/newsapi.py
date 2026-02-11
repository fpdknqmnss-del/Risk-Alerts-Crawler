import logging

import httpx

from app.config import settings
from app.sources.base import (
    NewsSourceAdapter,
    NormalizedNewsItem,
    make_json_serializable,
    normalize_datetime,
)

logger = logging.getLogger(__name__)


class NewsAPIAdapter(NewsSourceAdapter):
    source_name = "newsapi"
    base_url = "https://newsapi.org/v2/everything"

    async def fetch_recent(self, limit: int = 50) -> list[NormalizedNewsItem]:
        if not settings.NEWSAPI_KEY:
            logger.warning("Skipping NewsAPI fetch because NEWSAPI_KEY is not configured.")
            return []

        params = {
            "apiKey": settings.NEWSAPI_KEY,
            "language": "en",
            "pageSize": min(max(limit, 1), 100),
            "sortBy": "publishedAt",
            "q": "travel OR security OR unrest OR disaster OR outbreak",
        }

        async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()

        items: list[NormalizedNewsItem] = []
        for article in payload.get("articles", []):
            title = article.get("title")
            url = article.get("url")
            if not title or not url:
                continue

            source_info = article.get("source") or {}
            source_name = source_info.get("name") or self.source_name

            items.append(
                NormalizedNewsItem(
                    source=source_name,
                    title=title,
                    url=url,
                    description=article.get("description"),
                    content=article.get("content"),
                    published_at=normalize_datetime(article.get("publishedAt")),
                    country=None,
                    region=None,
                    latitude=None,
                    longitude=None,
                    payload=make_json_serializable(article),
                )
            )

        return items
