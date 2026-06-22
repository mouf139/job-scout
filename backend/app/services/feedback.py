import json
import logging
from datetime import datetime, timedelta, timezone

import anthropic
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.interview import _parse_json_response as _parse_json
from app.models.job_listing import JobListing
from app.models.user_job_selection import UserJobSelection
from app.models.job_outcome import JobOutcome
from app.models.preference_profile import PreferenceProfile

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

PROFILE_SYSTEM = """You are analyzing a user's job selection patterns to build a preference profile.
You will receive data about jobs the user selected vs. ignored, and any outcomes they reported.

Generate a preference profile as JSON:
{
  "preferred_companies": ["companies they tend to select"],
  "preferred_industries": ["industries they favor"],
  "preferred_title_keywords": ["keywords in titles they select"],
  "avoided_keywords": ["keywords in titles they ignore"],
  "salary_preference": "description of salary range preference",
  "location_preference": "description of location preference",
  "company_size_preference": "any pattern in company sizes",
  "key_insights": ["other patterns you notice"],
  "confidence": "low|medium|high based on data volume"
}

Return ONLY valid JSON."""

SCORING_SYSTEM = """You are scoring job listings based on a user's preference profile.
You will receive the preference profile and a list of job listings.

For each job, return a match score from 0-100 based on how well it matches the profile.
Return a JSON array of objects: [{"job_id": 1, "score": 85, "reason": "brief reason"}, ...]

Return ONLY valid JSON."""


async def has_enough_data(user_id: int, db: AsyncSession) -> bool:
    two_weeks_ago = datetime.utcnow() - timedelta(weeks=2)
    selection_count = await db.execute(
        select(func.count(UserJobSelection.id)).where(
            and_(
                UserJobSelection.user_id == user_id,
                UserJobSelection.selected_at >= two_weeks_ago,
            )
        )
    )
    count = selection_count.scalar() or 0
    return count >= 5


async def generate_preference_profile(user_id: int, db: AsyncSession) -> dict | None:
    if not settings.anthropic_api_key:
        return None

    # Get all jobs for user
    jobs_result = await db.execute(
        select(JobListing).where(JobListing.user_id == user_id).order_by(JobListing.found_at.desc()).limit(100)
    )
    all_jobs = jobs_result.scalars().all()

    # Get selected job IDs
    selections_result = await db.execute(
        select(UserJobSelection.job_listing_id).where(UserJobSelection.user_id == user_id)
    )
    selected_ids = {r[0] for r in selections_result.all()}

    # Get outcomes
    outcomes_result = await db.execute(
        select(JobOutcome).where(JobOutcome.user_id == user_id)
    )
    outcomes = {o.job_listing_id: o.status.value for o in outcomes_result.scalars().all()}

    selected_jobs = []
    ignored_jobs = []
    for job in all_jobs:
        job_data = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "salary": job.salary,
            "source": job.source,
        }
        if job.id in selected_ids:
            job_data["outcome"] = outcomes.get(job.id)
            selected_jobs.append(job_data)
        else:
            ignored_jobs.append(job_data)

    prompt = f"""Selected jobs ({len(selected_jobs)}):
{json.dumps(selected_jobs, indent=2)}

Ignored jobs ({len(ignored_jobs)}):
{json.dumps(ignored_jobs[:50], indent=2)}

Outcomes: {json.dumps({k: v for k, v in outcomes.items()}, indent=2)}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=PROFILE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    profile_data = _parse_json(message.content[0].text)

    # Save profile
    existing = await db.execute(
        select(PreferenceProfile).where(PreferenceProfile.user_id == user_id)
    )
    profile = existing.scalar_one_or_none()
    if profile:
        profile.profile_json = profile_data
        profile.last_updated = datetime.utcnow()
    else:
        db.add(PreferenceProfile(
            user_id=user_id,
            profile_json=profile_data,
        ))

    await db.commit()
    return profile_data


async def score_jobs(user_id: int, job_ids: list[int], db: AsyncSession) -> dict[int, int]:
    if not settings.anthropic_api_key:
        return {}

    profile_result = await db.execute(
        select(PreferenceProfile).where(PreferenceProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile or not profile.profile_json:
        return {}

    jobs_result = await db.execute(
        select(JobListing).where(JobListing.id.in_(job_ids))
    )
    jobs = jobs_result.scalars().all()

    jobs_data = [
        {
            "job_id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "salary": j.salary,
        }
        for j in jobs
    ]

    prompt = f"""Preference profile:
{json.dumps(profile.profile_json, indent=2)}

Jobs to score:
{json.dumps(jobs_data, indent=2)}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=SCORING_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    scores = _parse_json(message.content[0].text)
    return {s["job_id"]: s["score"] for s in scores}
