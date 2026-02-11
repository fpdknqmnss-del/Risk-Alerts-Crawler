from __future__ import annotations

import httpx

from app.config import settings
from app.sources.base import (
    NewsSourceAdapter,
    NormalizedNewsItem,
    make_json_serializable,
    normalize_datetime,
)


class USGSAdapter(NewsSourceAdapter):
    source_name = "usgs"

    async def fetch_recent(self, limit: int = 50) -> list[NormalizedNewsItem]:
        async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
            response = await client.get(settings.USGS_EARTHQUAKE_FEED_URL)
            response.raise_for_status()
            payload = response.json()

        items: list[NormalizedNewsItem] = []
        for feature in payload.get("features", [])[:limit]:
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            coordinates = geometry.get("coordinates") or []
            longitude = coordinates[0] if len(coordinates) > 0 else None
            latitude = coordinates[1] if len(coordinates) > 1 else None

            url = properties.get("url") or properties.get("detail")
            title = properties.get("title")
            if not title or not url:
                continue

            place = properties.get("place")
            country = None
            if isinstance(place, str) and "," in place:
                country = place.split(",")[-1].strip()

            items.append(
                NormalizedNewsItem(
                    source=self.source_name,
                    title=title,
                    url=url,
                    description=place if isinstance(place, str) else None,
                    content=properties.get("detail"),
                    published_at=normalize_datetime(properties.get("time")),
                    country=country,
                    region=place if isinstance(place, str) else None,
                    latitude=latitude,
                    longitude=longitude,
                    payload=make_json_serializable(feature),
                )
            )

        return items
