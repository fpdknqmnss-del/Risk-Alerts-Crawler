import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom_endpoint():
        raise RuntimeError("simulated error")

    @app.get("/http-error")
    async def http_error_endpoint():
        raise HTTPException(status_code=400, detail={"reason": "bad_input"})

    @app.get("/validation")
    async def validation_endpoint(limit: int):
        return {"limit": limit}

    return app


class ExceptionHandlerTests(unittest.TestCase):
    def test_http_exception_handler_preserves_detail_payload(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/http-error")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"detail": {"reason": "bad_input"}})

    def test_validation_exception_handler_returns_standard_shape(self) -> None:
        with TestClient(create_app()) as client:
            response = client.get("/validation")
            payload = response.json()

            self.assertEqual(response.status_code, 422)
            self.assertEqual(payload["detail"], "Validation failed")
            self.assertIsInstance(payload["errors"], list)
            self.assertGreater(len(payload["errors"]), 0)

    def test_unhandled_exception_returns_sanitized_500(self) -> None:
        with TestClient(create_app(), raise_server_exceptions=False) as client:
            response = client.get("/boom")
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.json(), {"detail": "Internal server error"})


if __name__ == "__main__":
    unittest.main()
