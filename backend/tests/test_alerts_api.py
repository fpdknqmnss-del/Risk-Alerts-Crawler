"""Tests for the alerts API endpoints (backend/app/api/alerts.py).

Covers:
- GET /alerts        – paginated list with category, severity, search filters
- GET /alerts/{id}   – single alert retrieval and 404 handling
- GET /alerts/stats  – aggregated statistics shape
- Authentication enforcement (401 when no/invalid token)
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.alerts import router
from app.database import get_db
from app.deps import get_current_user
from app.models.alert import Alert, AlertCategory
from app.models.user import User, UserRole
from app.schemas.alerts import AlertListResponse, AlertResponse, AlertsStatsResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_user(**overrides) -> User:
    defaults = dict(
        id=1,
        email="tester@example.com",
        password_hash="hashed",
        name="Test User",
        role=UserRole.VIEWER,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    user = MagicMock(spec=User)
    for key, value in defaults.items():
        setattr(user, key, value)
    return user


def _make_fake_alert(**overrides) -> MagicMock:
    """Return a MagicMock that quacks like an Alert ORM instance."""
    defaults = dict(
        id=1,
        title="Earthquake in Japan",
        summary="A 6.2 magnitude earthquake struck central Japan.",
        full_content="Extended details about the earthquake.",
        category=AlertCategory.NATURAL_DISASTER,
        severity=4,
        country="Japan",
        region="Kanto",
        latitude=35.6762,
        longitude=139.6503,
        sources=[{"name": "Reuters", "url": "https://reuters.com/article"}],
        verified=True,
        verification_score=0.85,
        created_at=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 6, 1, 12, 5, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    alert = MagicMock(spec=Alert)
    for key, value in defaults.items():
        setattr(alert, key, value)
    # Pydantic model_validate calls from_attributes; we expose a dict too
    alert.__dict__.update(defaults)
    return alert


def _create_app(
    *,
    override_user: User | None = None,
    override_db: AsyncMock | None = None,
) -> FastAPI:
    """Build a minimal FastAPI app wired to the alerts router with mocked deps."""
    app = FastAPI()
    app.include_router(router)

    # Auth dependency override
    if override_user is not None:
        app.dependency_overrides[get_current_user] = lambda: override_user
    # else: leave un-overridden so the real dependency rejects unauthenticated requests

    # Database session override
    if override_db is not None:
        app.dependency_overrides[get_db] = lambda: override_db

    return app


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

class TestListAlerts(unittest.TestCase):
    """GET /alerts – paginated listing with optional filters."""

    def _setup_db_mock(self, alerts: list, total: int) -> AsyncMock:
        db = AsyncMock()
        # db.scalar(count_query) → total
        db.scalar = AsyncMock(return_value=total)
        # db.scalars(data_query).all() → list of alerts
        scalars_result = MagicMock()
        scalars_result.all.return_value = alerts
        db.scalars = AsyncMock(return_value=scalars_result)
        return db

    def test_returns_paginated_response_shape(self) -> None:
        """Happy-path: returns items, total, page, page_size."""
        alert = _make_fake_alert()
        db = self._setup_db_mock(alerts=[alert], total=1)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("items", body)
        self.assertIn("total", body)
        self.assertIn("page", body)
        self.assertIn("page_size", body)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["page"], 1)
        self.assertEqual(len(body["items"]), 1)

    def test_empty_result_returns_zero_items(self) -> None:
        db = self._setup_db_mock(alerts=[], total=0)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 0)
        self.assertEqual(body["items"], [])

    def test_category_filter_passed_as_query_param(self) -> None:
        """Ensure the category query param is accepted without error."""
        db = self._setup_db_mock(alerts=[], total=0)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts", params={"category": "health"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], 0)

    def test_invalid_category_returns_422(self) -> None:
        db = self._setup_db_mock(alerts=[], total=0)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts", params={"category": "nonexistent"})

        self.assertEqual(resp.status_code, 422)

    def test_severity_filter_accepted(self) -> None:
        db = self._setup_db_mock(alerts=[], total=0)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts", params={"severity_min": 3, "severity_max": 5})

        self.assertEqual(resp.status_code, 200)

    def test_severity_out_of_range_returns_422(self) -> None:
        db = self._setup_db_mock(alerts=[], total=0)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts", params={"severity_min": 0})

        self.assertEqual(resp.status_code, 422)

    def test_search_filter_accepted(self) -> None:
        db = self._setup_db_mock(alerts=[], total=0)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts", params={"search": "earthquake"})

        self.assertEqual(resp.status_code, 200)

    def test_pagination_params(self) -> None:
        db = self._setup_db_mock(alerts=[], total=50)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts", params={"page": 2, "page_size": 10})

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["page_size"], 10)
        self.assertEqual(body["total"], 50)

    def test_alert_response_item_shape(self) -> None:
        """Verify the serialized alert contains all expected fields."""
        alert = _make_fake_alert()
        db = self._setup_db_mock(alerts=[alert], total=1)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts")

        item = resp.json()["items"][0]
        expected_keys = {
            "id", "title", "summary", "full_content", "category",
            "severity", "country", "region", "latitude", "longitude",
            "sources", "verified", "verification_score",
            "created_at", "updated_at",
        }
        self.assertTrue(expected_keys.issubset(set(item.keys())))
        self.assertEqual(item["category"], "natural_disaster")
        self.assertEqual(item["severity"], 4)


class TestGetAlert(unittest.TestCase):
    """GET /alerts/{alert_id} – single alert retrieval."""

    def test_returns_alert_when_found(self) -> None:
        alert = _make_fake_alert(id=42)
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=alert)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts/42")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["id"], 42)
        self.assertEqual(body["title"], "Earthquake in Japan")

    def test_get_alert_by_id_not_found(self) -> None:
        """GET /alerts/999 returns 404."""
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts/999")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Alert not found")

    def test_returns_404_when_not_found(self) -> None:
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts/9999")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Alert not found")


class TestGetAlertStats(unittest.TestCase):
    """GET /alerts/stats – aggregated statistics."""

    def _setup_stats_db(
        self,
        total: int = 10,
        critical: int = 2,
        countries: int = 5,
        severity_rows: list | None = None,
        category_rows: list | None = None,
    ) -> AsyncMock:
        db = AsyncMock()

        # db.scalar is called three times (total, critical, countries)
        db.scalar = AsyncMock(side_effect=[total, critical, countries])

        # db.execute is called twice (severity_distribution, category_distribution)
        sev_result = MagicMock()
        sev_result.all.return_value = severity_rows or [(3, 5), (4, 3), (5, 2)]
        cat_result = MagicMock()
        cat_result.all.return_value = category_rows or [
            (AlertCategory.NATURAL_DISASTER, 4),
            (AlertCategory.HEALTH, 3),
            (AlertCategory.TERRORISM, 3),
        ]
        db.execute = AsyncMock(side_effect=[sev_result, cat_result])
        return db

    def test_returns_stats_shape(self) -> None:
        db = self._setup_stats_db()
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts/stats")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("total_alerts", body)
        self.assertIn("critical_alerts", body)
        self.assertIn("countries_affected", body)
        self.assertIn("severity_distribution", body)
        self.assertIn("category_distribution", body)
        self.assertEqual(body["total_alerts"], 10)
        self.assertEqual(body["critical_alerts"], 2)
        self.assertEqual(body["countries_affected"], 5)

    def test_severity_distribution_items(self) -> None:
        db = self._setup_stats_db(severity_rows=[(1, 2), (5, 8)])
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts/stats")

        dist = resp.json()["severity_distribution"]
        self.assertEqual(len(dist), 2)
        self.assertEqual(dist[0]["severity"], 1)
        self.assertEqual(dist[0]["count"], 2)

    def test_category_distribution_items(self) -> None:
        db = self._setup_stats_db(
            category_rows=[(AlertCategory.CRIME, 7)],
        )
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts/stats")

        dist = resp.json()["category_distribution"]
        self.assertEqual(len(dist), 1)
        self.assertEqual(dist[0]["category"], "crime")

    def test_empty_stats(self) -> None:
        db = self._setup_stats_db(
            total=0, critical=0, countries=0,
            severity_rows=[], category_rows=[],
        )
        app = _create_app(override_user=_make_fake_user(), override_db=db)

        with TestClient(app) as client:
            resp = client.get("/alerts/stats")

        body = resp.json()
        self.assertEqual(body["total_alerts"], 0)
        self.assertEqual(body["severity_distribution"], [])
        self.assertEqual(body["category_distribution"], [])


class TestAlertsAuthentication(unittest.TestCase):
    """Verify that unauthenticated requests are rejected."""

    def _build_unauthenticated_app(self) -> FastAPI:
        """App with NO auth override – real dependency requires credentials."""
        app = FastAPI()
        app.include_router(router)
        # Override DB so we don't need a real database
        db = AsyncMock()
        app.dependency_overrides[get_db] = lambda: db
        # get_current_user is NOT overridden → will check for Bearer token
        return app

    def test_list_alerts_requires_auth(self) -> None:
        """GET /alerts without token returns 401/403."""
        app = self._build_unauthenticated_app()
        with TestClient(app) as client:
            resp = client.get("/alerts")
        self.assertIn(resp.status_code, (401, 403))

    def test_get_alert_stats_requires_auth(self) -> None:
        """GET /alerts/stats without token returns 401/403."""
        app = self._build_unauthenticated_app()
        with TestClient(app) as client:
            resp = client.get("/alerts/stats")
        self.assertIn(resp.status_code, (401, 403))

    def test_get_alert_unauthenticated_returns_401_or_403(self) -> None:
        app = self._build_unauthenticated_app()
        with TestClient(app) as client:
            resp = client.get("/alerts/1")
        self.assertIn(resp.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()
