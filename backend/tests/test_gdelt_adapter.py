"""Tests for the GDELT adapter (backend/app/sources/gdelt.py).

Uses unittest.mock.AsyncMock and patch to mock httpx responses.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.sources.gdelt import GDELTAdapter


class TestGDELTAdapter(unittest.TestCase):
    """GDELTAdapter fetch_recent tests with mocked HTTP."""

    def test_fetch_recent_parses_articles(self) -> None:
        """Mock httpx response with sample GDELT JSON, verify NormalizedNewsItem fields."""
        sample_response = {
            "articles": [
                {
                    "title": "Earthquake strikes Japan",
                    "url": "https://example.com/article1",
                    "domain": "example.com",
                    "seendate": "2025-02-10T12:00:00Z",
                    "sourcecountry": "Japan",
                },
                {
                    "title": "Political unrest in region",
                    "url": "https://news.org/item/456",
                    "domain": "news.org",
                    "seendate": "2025-02-10T11:30:00",
                    "sourcecountry": "UK",
                },
            ]
        }

        mock_response = AsyncMock()
        mock_response.json.return_value = sample_response
        mock_response.raise_for_status = AsyncMock()

        with patch("app.sources.gdelt.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            adapter = GDELTAdapter()
            items = asyncio.run(adapter.fetch_recent(limit=10))

        self.assertEqual(len(items), 2)

        item1 = items[0]
        self.assertEqual(item1.title, "Earthquake strikes Japan")
        self.assertEqual(item1.url, "https://example.com/article1")
        self.assertEqual(item1.source, "example.com")
        self.assertEqual(item1.country, "Japan")
        self.assertIn("Article from example.com", item1.description or "")

        item2 = items[1]
        self.assertEqual(item2.title, "Political unrest in region")
        self.assertEqual(item2.url, "https://news.org/item/456")
        self.assertEqual(item2.source, "news.org")
        self.assertEqual(item2.country, "UK")

    def test_fetch_recent_skips_items_without_title(self) -> None:
        """Items missing title should be skipped."""
        sample_response = {
            "articles": [
                {"title": "Valid article", "url": "https://example.com/1"},
                {"url": "https://example.com/2"},
                {"title": "", "url": "https://example.com/3"},
                {"title": "Another valid", "url": "https://example.com/4"},
            ]
        }

        mock_response = AsyncMock()
        mock_response.json.return_value = sample_response
        mock_response.raise_for_status = AsyncMock()

        with patch("app.sources.gdelt.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            adapter = GDELTAdapter()
            items = asyncio.run(adapter.fetch_recent(limit=10))

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Valid article")
        self.assertEqual(items[1].title, "Another valid")

    def test_fetch_recent_skips_items_without_url(self) -> None:
        """Items missing url should be skipped."""
        sample_response = {
            "articles": [
                {"title": "No URL", "domain": "example.com"},
                {"title": "Has URL", "url": "https://example.com/ok"},
            ]
        }

        mock_response = AsyncMock()
        mock_response.json.return_value = sample_response
        mock_response.raise_for_status = AsyncMock()

        with patch("app.sources.gdelt.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            adapter = GDELTAdapter()
            items = asyncio.run(adapter.fetch_recent(limit=10))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Has URL")

    def test_fetch_recent_handles_empty_response(self) -> None:
        """Empty articles list returns empty."""
        mock_response = AsyncMock()
        mock_response.json.return_value = {"articles": []}
        mock_response.raise_for_status = AsyncMock()

        with patch("app.sources.gdelt.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            adapter = GDELTAdapter()
            items = asyncio.run(adapter.fetch_recent(limit=10))

        self.assertEqual(len(items), 0)


if __name__ == "__main__":
    unittest.main()
