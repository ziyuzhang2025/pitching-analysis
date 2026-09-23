"""Worked example model (agent-written). Copy this pattern for the exercise models."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Athlete(Base):
    __tablename__ = "athletes"
    __table_args__ = (
        CheckConstraint("throwing_hand IN ('right', 'left')", name="throwing_hand"),
        CheckConstraint("height_m IS NULL OR (height_m > 1.0 AND height_m < 2.5)",
                        name="height_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    throwing_hand: Mapped[str] = mapped_column(String(5), nullable=False)
    height_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
