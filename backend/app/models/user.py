import enum
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    google_drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_drive_folder_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    search_criteria = relationship("SearchCriteria", back_populates="user", uselist=False)
    resumes = relationship("Resume", back_populates="user")
    resume_extraction = relationship("ResumeExtraction", back_populates="user", uselist=False)
    interview_sessions = relationship("InterviewSession", back_populates="user")
    job_listings = relationship("JobListing", back_populates="user")
    job_selections = relationship("UserJobSelection", back_populates="user")
    tailored_resumes = relationship("TailoredResume", back_populates="user")
    preference_profile = relationship("PreferenceProfile", back_populates="user", uselist=False)
    job_outcomes = relationship("JobOutcome", back_populates="user")
    pipeline_runs = relationship("PipelineRun", back_populates="user")
