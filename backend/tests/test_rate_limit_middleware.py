import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import RateLimitMiddleware


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=2,
        window_seconds=60,
        enabled=True,
        exempt_paths=["/health"],
    )

    @app.get("/limited")
    async def limited_endpoint():
        return {"ok": True}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "healthy"}

    return app


class RateLimitMiddlewareTests(unittest.TestCase):
    def test_blocks_requests_when_limit_exceeded(self) -> None:
        with TestClient(create_app()) as client:
            first = client.get("/limited")
            second = client.get("/limited")
            third = client.get("/limited")

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(third.status_code, 429)
            self.assertIn("Retry-After", third.headers)
            self.assertEqual(third.headers.get("X-RateLimit-Remaining"), "0")

    def test_exempt_paths_are_not_limited(self) -> None:
        with TestClient(create_app()) as client:
            responses = [client.get("/health") for _ in range(5)]
            self.assertTrue(all(response.status_code == 200 for response in responses))


if __name__ == "__main__":
    unittest.main()
