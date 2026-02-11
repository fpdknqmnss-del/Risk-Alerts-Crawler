from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.alert import AlertCategory
from app.models.report import ReportStatus


class ReportGenerationRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=500)
    geographic_scope: str | None = Field(default=None, max_length=500)
    date_range_start: date | None = None
    date_range_end: date | None = None
    categories: list[AlertCategory] = Field(default_factory=list)
    max_alerts: int = Field(default=50, ge=1, le=200)
    include_unverified: bool = False
    generate_pdf: bool = True

    @model_validator(mode="after")
    def validate_date_range(self) -> "ReportGenerationRequest":
        if (
            self.date_range_start is not None
            and self.date_range_end is not None
            and self.date_range_end < self.date_range_start
        ):
            raise ValueError("date_range_end must be on or after date_range_start")
        return self


class ReportCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    summary: str | None = Field(default=None, max_length=20000)
    content_json: dict[str, Any] | None = None
    geographic_scope: str | None = Field(default=None, max_length=500)
    date_range_start: date | None = None
    date_range_end: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "ReportCreateRequest":
        if (
            self.date_range_start is not None
            and self.date_range_end is not None
            and self.date_range_end < self.date_range_start
        ):
            raise ValueError("date_range_end must be on or after date_range_start")
        return self


class ReportResponse(BaseModel):
    id: int
    title: str
    summary: str | None
    content_json: dict[str, Any] | None
    pdf_path: str | None
    status: ReportStatus
    created_by: int
    approved_by: int | None
    geographic_scope: str | None
    date_range_start: datetime | None
    date_range_end: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportGenerationResponse(BaseModel):
    report: ReportResponse
    alerts_used: int


class ReportApprovalRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=5000)


class ReportDispatchRequest(BaseModel):
    mailing_list_ids: list[int] = Field(default_factory=list)
    use_geographic_match: bool = True


class ReportDispatchResponse(BaseModel):
    task_id: str | None
    status: str
