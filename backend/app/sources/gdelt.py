import httpx

from app.config import settings
from app.sources.base import (
    NewsSourceAdapter,
    NormalizedNewsItem,
    make_json_serializable,
    normalize_datetime,
)


class GDELTAdapter(NewsSourceAdapter):
    source_name = "gdelt"

    async def fetch_recent(self, limit: int = 50) -> list[NormalizedNewsItem]:
        endpoint = f"{settings.GDELT_BASE_URL.rstrip('/')}/doc/doc"
        params = {
            "query": "travel OR security OR unrest OR disaster",
            "mode": "artlist",
            "maxrecords": min(max(limit, 1), 250),
            "format": "json",
            "sort": "datedesc",
        }

        async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()

        items: list[NormalizedNewsItem] = []
        for article in payload.get("articles", []):
            title = article.get("title")
            url = article.get("url")
            if not title or not url:
                continue

            domain = article.get("domain")
            description = f"Article from {domain}: {title}" if domain else None

            items.append(
                NormalizedNewsItem(
                    source=article.get("domain", self.source_name),
                    title=title,
                    url=url,
                    description=description,
                    content=None,
                    published_at=normalize_datetime(article.get("seendate")),
                    country=article.get("sourcecountry"),
                    region=None,
                    latitude=None,
                    longitude=None,
                    payload=make_json_serializable(article),
                )
            )

        return items
