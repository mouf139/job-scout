from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    must_change_password: bool
    onboarding_completed: bool
    created_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    is_active: bool | None = None


class UserAdminView(UserOut):
    jobs_found: int = 0
    resumes_generated: int = 0
    last_run: datetime | None = None
    last_error: str | None = None
