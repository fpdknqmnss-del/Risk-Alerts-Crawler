from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


@dataclass(slots=True)
class NormalizedNewsItem:
    source: str
    title: str
    url: str
    description: str | None
    content: str | None
    published_at: datetime | None
    country: str | None
    region: str | None
    latitude: float | None
    longitude: float | None
    payload: dict[str, Any]


class NewsSourceAdapter(ABC):
    source_name: str

    def __init__(self, request_timeout_seconds: float = 20.0) -> None:
        self.request_timeout_seconds = request_timeout_seconds

    @abstractmethod
    async def fetch_recent(self, limit: int = 50) -> list[NormalizedNewsItem]:
        """Fetch and normalize recent source items."""


def make_json_serializable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        normalized = normalize_datetime(value)
        return normalized.isoformat() if normalized else None

    if isinstance(value, dict):
        return {
            str(key): make_json_serializable(raw_value)
            for key, raw_value in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [make_json_serializable(raw_item) for raw_item in value]

    return str(value)


def normalize_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        dt_value = value
    elif isinstance(value, (int, float)):
        timestamp = float(value)
        # Some APIs return milliseconds since epoch.
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000.0
        dt_value = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    elif isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            dt_value = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt_value = parsedate_to_datetime(cleaned)
            except (TypeError, ValueError):
                for datetime_format in ("%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        dt_value = datetime.strptime(cleaned, datetime_format)
                        break
                    except ValueError:
                        continue
                else:
                    return None
    else:
        return None

    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)
