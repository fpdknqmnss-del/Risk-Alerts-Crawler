import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlertCategory(str, enum.Enum):
    NATURAL_DISASTER = "natural_disaster"
    POLITICAL = "political"
    CRIME = "crime"
    HEALTH = "health"
    TERRORISM = "terrorism"
    CIVIL_UNREST = "civil_unrest"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_content: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[AlertCategory] = mapped_column(
        Enum(AlertCategory, values_callable=lambda e: [member.value for member in e]),
        nullable=False,
        index=True,
    )
    severity: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)
    location = mapped_column(
        Geometry(geometry_type="POINT", srid=4326), nullable=True
    )
    sources: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_score: Mapped[float] = mapped_column(
        Float, nullable=True, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, title={self.title[:50]}, severity={self.severity})>"
