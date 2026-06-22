from pydantic import BaseModel


class SearchCriteriaOut(BaseModel):
    titles: list[str] | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    location: str | None = None
    radius_miles: int | None = None
    remote_preference: str | None = None
    experience_level: str | None = None
    job_type: str | None = None
    salary_minimum: int | None = None
    industries: list[str] | None = None
    timezone: str | None = "America/New_York"
    digest_time: str | None = None
    email_notifications_enabled: bool = False

    model_config = {"from_attributes": True}


class SearchCriteriaUpdate(BaseModel):
    titles: list[str] | None = None
    include_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    location: str | None = None
    radius_miles: int | None = None
    remote_preference: str | None = None
    experience_level: str | None = None
    job_type: str | None = None
    salary_minimum: int | None = None
    industries: list[str] | None = None
    timezone: str | None = None
    digest_time: str | None = None
    email_notifications_enabled: bool | None = None
