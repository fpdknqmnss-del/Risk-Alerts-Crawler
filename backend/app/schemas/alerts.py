from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.models.alert import AlertCategory


class AlertResponse(BaseModel):
    id: int
    title: str
    summary: str
    full_content: str | None
    category: AlertCategory
    severity: int
    country: str
    region: str | None
    latitude: float | None
    longitude: float | None
    sources: list[dict] | dict | None = Field(default_factory=list)
    verified: bool
    verification_score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertSortBy(str, Enum):
    CREATED_AT = "created_at"
    SEVERITY = "severity"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int


class SeverityDistributionItem(BaseModel):
    severity: int
    count: int


class CategoryDistributionItem(BaseModel):
    category: AlertCategory
    count: int


class AlertsStatsResponse(BaseModel):
    total_alerts: int
    critical_alerts: int
    countries_affected: int
    severity_distribution: list[SeverityDistributionItem]
    category_distribution: list[CategoryDistributionItem]
