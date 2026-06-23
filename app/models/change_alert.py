from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, func, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChangeAlert(Base):
    """
    A detected change in visa policy for a tracked VisaCase.
    Created by the scheduled refresh job when a diff is found.
    """

    __tablename__ = "change_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    visa_case_id: Mapped[int] = mapped_column(
        ForeignKey("visa_cases.id"), nullable=False, index=True
    )

    # What changed
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    change_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "new_requirement", "fee_change", "processing_time", "restriction"
    summary: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # LLM plain-language summary
    raw_diff: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # the actual before/after text diff
    action_required: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # what the user should do

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    severity: Mapped[str] = mapped_column(
        String(20), default="info"
    )  # info | warning | critical

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    visa_case: Mapped["VisaCase"] = relationship(back_populates="change_alerts")

    def __repr__(self) -> str:
        return f"<ChangeAlert id={self.id} type={self.change_type} severity={self.severity}>"
