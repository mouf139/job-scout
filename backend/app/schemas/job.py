from datetime import datetime

from pydantic import BaseModel


class JobListingOut(BaseModel):
    id: int
    title: str
    company: str
    location: str | None = None
    salary: str | None = None
    posting_date: datetime | None = None
    description: str | None = None
    apply_options_json: list | None = None
    source: str | None = None
    found_at: datetime
    is_active: bool
    match_score: int | None = None
    is_new: bool = True

    model_config = {"from_attributes": True}


class JobSelectionRequest(BaseModel):
    job_listing_ids: list[int]


class JobOutcomeUpdate(BaseModel):
    status: str
