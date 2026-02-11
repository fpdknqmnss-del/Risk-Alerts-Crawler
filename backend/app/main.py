from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.api import admin_router, alerts_router, auth_router, mailing_router, reports_router
from app.config import settings
from app.database import async_session
from app.exceptions import register_exception_handlers
from app.middleware import RateLimitMiddleware
from app.models.alert import Alert
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    start_scheduler()
    yield
    # Shutdown
    from app.database import engine

    stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title="Risk Alerts Platform",
    description="Travel risk alert aggregation and reporting platform",
    version="1.0.0",
    lifespan=lifespan,
)
register_exception_handlers(app)

app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    enabled=settings.RATE_LIMIT_ENABLED,
    exempt_paths=settings.rate_limit_exempt_paths_list,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(mailing_router)
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


@app.get("/health/db")
async def db_health_check():
    """Database connectivity health check."""
    from sqlalchemy import text

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


async def _alerts_snapshot() -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(
                func.count(Alert.id),
                func.max(Alert.id),
                func.max(Alert.created_at),
            )
        )
        total_alerts, latest_alert_id, latest_alert_at = result.one()

    return {
        "total_alerts": int(total_alerts or 0),
        "latest_alert_id": int(latest_alert_id or 0),
        "latest_alert_at": latest_alert_at.isoformat() if latest_alert_at else None,
    }


@app.websocket("/ws")
async def alerts_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    previous_snapshot: dict | None = None

    try:
        while True:
            snapshot = await _alerts_snapshot()
            if snapshot != previous_snapshot:
                await websocket.send_json({"type": "alerts_updated", "data": snapshot})
                previous_snapshot = snapshot
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("Unhandled error in alerts WebSocket connection")
        await websocket.close(code=1011)
