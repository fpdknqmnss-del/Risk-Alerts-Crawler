"""Tests for the auth API endpoints (backend/app/api/auth.py).

Covers:
- POST /auth/register – user registration
- POST /auth/login – login with credentials
- GET /auth/me – current user (requires auth)
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import router
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User, UserRole


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


def _create_app(
    *,
    override_user: User | None = None,
    override_db: AsyncMock | None = None,
) -> FastAPI:
    """Build a minimal FastAPI app with auth router and mocked deps."""
    app = FastAPI()
    app.include_router(router)

    if override_user is not None:
        app.dependency_overrides[get_current_user] = lambda: override_user
    if override_db is not None:
        app.dependency_overrides[get_db] = lambda: override_db

    return app


class TestAuthRegister(unittest.TestCase):
    """POST /auth/register – user registration."""

    def test_register_returns_201(self) -> None:
        """Mock DB to return no existing user, test POST /auth/register."""
        db = AsyncMock()
        db.scalar = AsyncMock(side_effect=[None, 0])

        async def refresh_user(user):
            user.id = 1
            user.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)

        db.add = MagicMock()
        db.flush = AsyncMock(return_value=None)
        db.refresh = AsyncMock(side_effect=refresh_user)

        app = _create_app(override_db=db)

        with TestClient(app) as client:
            resp = client.post(
                "/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecurePass123!",
                    "name": "New User",
                },
            )

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn("id", body)
        self.assertEqual(body["email"], "newuser@example.com")
        self.assertEqual(body["name"], "New User")


class TestAuthLogin(unittest.TestCase):
    """POST /auth/login – login with credentials."""

    def test_login_with_invalid_credentials(self) -> None:
        """Test POST /auth/login returns 401 for invalid credentials."""
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=None)
        app = _create_app(override_db=db)

        with TestClient(app) as client:
            resp = client.post(
                "/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "wrongpassword",
                },
            )

        self.assertEqual(resp.status_code, 401)
        self.assertIn("detail", resp.json())


class TestAuthMe(unittest.TestCase):
    """GET /auth/me – current user (requires auth)."""

    def test_me_without_token(self) -> None:
        """Test GET /auth/me returns 401/403 when no token provided."""
        db = AsyncMock()
        app = _create_app(override_db=db)
        # get_current_user is NOT overridden – will reject unauthenticated requests

        with TestClient(app) as client:
            resp = client.get("/auth/me")

        self.assertIn(resp.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()
