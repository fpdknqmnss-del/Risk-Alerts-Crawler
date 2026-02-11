from __future__ import annotations

import httpx

from app.config import settings
from app.sources.base import (
    NewsSourceAdapter,
    NormalizedNewsItem,
    make_json_serializable,
    normalize_datetime,
)


class ReliefWebAdapter(NewsSourceAdapter):
    source_name = "reliefweb"

    async def fetch_recent(self, limit: int = 50) -> list[NormalizedNewsItem]:
        endpoint = f"{settings.RELIEFWEB_BASE_URL.rstrip('/')}/reports"
        params = {
            "appname": "risk-alert-platform",
            "limit": min(max(limit, 1), 100),
            "sort[]": "date:desc",
        }

        async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()

        items: list[NormalizedNewsItem] = []
        for item in payload.get("data", []):
            fields = item.get("fields") or {}
            title = fields.get("title")
            if not title:
                continue

            url = fields.get("url") or fields.get("url_alias")
            if not url:
                continue
            if isinstance(url, str) and url.startswith("/"):
                url = f"https://reliefweb.int{url}"

            country = None
            countries = fields.get("country") or []
            if countries:
                first_country = countries[0]
                country = first_country.get("name") if isinstance(first_country, dict) else None

            sources = fields.get("source") or []
            source_name = self.source_name
            if sources:
                first_source = sources[0]
                if isinstance(first_source, dict):
                    source_name = first_source.get("name") or source_name

            date_info = fields.get("date") or {}
            published_at = normalize_datetime(
                date_info.get("original") or date_info.get("created")
            )

            body = fields.get("body")
            description = body[:400] if isinstance(body, str) else None

            items.append(
                NormalizedNewsItem(
                    source=source_name,
                    title=title,
                    url=url,
                    description=description,
                    content=body if isinstance(body, str) else None,
                    published_at=published_at,
                    country=country,
                    region=None,
                    latitude=None,
                    longitude=None,
                    payload=make_json_serializable(item),
                )
            )

        return items
