from datetime import datetime

from pydantic import BaseModel, Field


class MailingListCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geographic_regions: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=5000)


class MailingListUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geographic_regions: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=5000)


class MailingListResponse(BaseModel):
    id: int
    name: str
    geographic_regions: list[str]
    description: str | None
    created_by: int
    created_at: datetime
    subscriber_count: int = 0

    model_config = {"from_attributes": True}


class SubscriberCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)


class SubscriberResponse(BaseModel):
    id: int
    email: str
    name: str | None
    organization: str | None
    mailing_list_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CsvImportResponse(BaseModel):
    total_rows: int
    imported_count: int
    skipped_count: int
    invalid_rows: int
