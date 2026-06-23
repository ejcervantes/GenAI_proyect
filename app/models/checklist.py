from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Checklist(Base):
    """
    A generated document checklist for a specific VisaCase.
    One case can have multiple checklist versions (regenerated over time).
    """

    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    visa_case_id: Mapped[int] = mapped_column(
        ForeignKey("visa_cases.id"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Document Checklist"
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )  # 0.0 - 1.0
    sources: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON list of source URLs

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    visa_case: Mapped["VisaCase"] = relationship(back_populates="checklists")
    items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="ChecklistItem.order",
    )

    def __repr__(self) -> str:
        return f"<Checklist id={self.id} case_id={self.visa_case_id}>"


class ChecklistItem(Base):
    """
    A single document requirement within a checklist.
    """

    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    checklist_id: Mapped[int] = mapped_column(
        ForeignKey("checklists.id"), nullable=False, index=True
    )

    order: Mapped[int] = mapped_column(Integer, default=0)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    is_conditional: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # e.g. "Required if staying > 90 days"
    requires_translation: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_notarization: Mapped[bool] = mapped_column(Boolean, default=False)

    # User progress
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    checklist: Mapped["Checklist"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<ChecklistItem id={self.id} '{self.document_name}' mandatory={self.is_mandatory}>"
