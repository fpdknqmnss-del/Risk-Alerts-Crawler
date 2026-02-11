from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class InMemoryRateLimiter:
    """Simple sliding-window in-memory rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max(max_requests, 1)
        self.window_seconds = max(window_seconds, 1)
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> tuple[bool, int, int]:
        """
        Returns (allowed, remaining, retry_after_seconds).

        retry_after_seconds is 0 when request is allowed.
        """
        now = time.monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            request_times = self._requests[key]
            while request_times and request_times[0] <= window_start:
                request_times.popleft()

            if len(request_times) >= self.max_requests:
                retry_after = max(int(request_times[0] + self.window_seconds - now), 1)
                return False, 0, retry_after

            request_times.append(now)
            remaining = max(self.max_requests - len(request_times), 0)
            return True, remaining, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_requests: int,
        window_seconds: int,
        enabled: bool = True,
        exempt_paths: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.exempt_paths = tuple(exempt_paths or ())
        self.limiter = InMemoryRateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        self.max_requests = max(max_requests, 1)
        self.window_seconds = max(window_seconds, 1)

    def _is_exempt_path(self, path: str) -> bool:
        return any(path == exempt_path or path.startswith(f"{exempt_path}/") for exempt_path in self.exempt_paths)

    @staticmethod
    def _client_key(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip

        if request.client and request.client.host:
            return request.client.host
        return "anonymous"

    def _apply_limit_headers(self, response: Response, remaining: int) -> None:
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if (
            not self.enabled
            or request.method.upper() == "OPTIONS"
            or self._is_exempt_path(request.url.path)
        ):
            return await call_next(request)

        allowed, remaining, retry_after = self.limiter.check(self._client_key(request))
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": str(self.window_seconds),
                },
            )

        response = await call_next(request)
        self._apply_limit_headers(response, remaining)
        return response
