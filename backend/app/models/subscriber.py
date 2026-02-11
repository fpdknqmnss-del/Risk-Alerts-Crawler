from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Subscriber(Base):
    __tablename__ = "subscribers"
    __table_args__ = (
        UniqueConstraint("email", "mailing_list_id", name="uq_subscriber_email_list"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    organization: Mapped[str] = mapped_column(String(255), nullable=True)
    mailing_list_id: Mapped[int] = mapped_column(
        ForeignKey("mailing_lists.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    mailing_list: Mapped["MailingList"] = relationship(
        "MailingList", back_populates="subscribers"
    )

    def __repr__(self) -> str:
        return f"<Subscriber(id={self.id}, email={self.email})>"
