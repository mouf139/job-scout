import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OutcomeStatus(str, enum.Enum):
    applied = "applied"
    heard_back = "heard_back"
    interview = "interview"
    rejected = "rejected"


class JobOutcome(Base):
    __tablename__ = "job_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    job_listing_id: Mapped[int] = mapped_column(ForeignKey("job_listings.id", ondelete="CASCADE"))
    status: Mapped[OutcomeStatus] = mapped_column(Enum(OutcomeStatus))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="job_outcomes")
    job_listing = relationship("JobListing", back_populates="outcomes")
