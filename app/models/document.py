from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    """
    Represents a user-uploaded file: a passport scan, national ID, or blank visa form.
    Extracted fields are stored as JSON in `extracted_data`.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(
        String(512), nullable=False
    )  # local path or object storage key
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "passport", "national_id", "visa_form"
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Extraction results (stored as JSON string)
    extracted_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )  # overall confidence
    extraction_status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending | processing | done | failed

    # For visa forms — filled form output path
    filled_form_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    fill_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # pending | done | failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.file_type} status={self.extraction_status}>"
