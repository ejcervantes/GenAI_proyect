from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, func, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RAGInteraction(Base):
    """
    Logs every conversational Q&A interaction.
    Useful for the benchmark evaluation and for auditing confidence/citations.
    """

    __tablename__ = "rag_interactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    # The question + context
    question: Mapped[str] = mapped_column(Text, nullable=False)
    passport_nationality: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    destination_country: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    travel_purpose: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # The answer
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0.0 - 1.0
    sources: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON list of citations

    # Retrieval metadata
    chunks_retrieved: Mapped[Optional[int]] = mapped_column(nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    was_mocked: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="rag_interactions")

    def __repr__(self) -> str:
        return f"<RAGInteraction id={self.id} confidence={self.confidence_score}>"
