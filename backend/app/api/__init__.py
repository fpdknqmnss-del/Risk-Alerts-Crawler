from app.api.auth import router as auth_router
from app.api.alerts import router as alerts_router
from app.api.reports import router as reports_router
from app.api.mailing import router as mailing_router
from app.api.admin import router as admin_router

__all__ = ["auth_router", "alerts_router", "reports_router", "mailing_router", "admin_router"]
