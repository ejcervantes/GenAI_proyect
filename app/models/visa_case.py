from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VisaCase(Base):
    """
    Represents a saved visa scenario for a user:
    e.g. Pakistani passport → Germany → Student visa
    This is the core entity that drives Q&A, checklists, and change tracking.
    """

    __tablename__ = "visa_cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # The case triple
    passport_nationality: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(100), nullable=False)
    travel_purpose: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "student", "tourist", "work"
    visa_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g. "Schengen", "D-Visa"

    # Additional context
    travel_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    residence_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Change tracking
    is_tracking: Mapped[bool] = mapped_column(default=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="visa_cases")
    checklists: Mapped[list["Checklist"]] = relationship(
        back_populates="visa_case", cascade="all, delete-orphan"
    )
    change_alerts: Mapped[list["ChangeAlert"]] = relationship(
        back_populates="visa_case", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<VisaCase id={self.id} {self.passport_nationality}→{self.destination_country} ({self.travel_purpose})>"
