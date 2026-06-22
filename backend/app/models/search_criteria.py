from datetime import time

from sqlalchemy import ForeignKey, String, Integer, Boolean, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SearchCriteria(Base):
    __tablename__ = "search_criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    titles: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    include_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    exclude_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    radius_miles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remote_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    salary_minimum: Mapped[int | None] = mapped_column(Integer, nullable=True)
    industries: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), default="America/New_York")
    digest_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="search_criteria")
