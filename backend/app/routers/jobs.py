from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.job_listing import JobListing
from app.models.user_job_selection import UserJobSelection
from app.models.job_outcome import JobOutcome, OutcomeStatus
from app.schemas.job import JobListingOut, JobSelectionRequest, JobOutcomeUpdate
from app.services.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=list[JobListingOut])
async def get_jobs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    five_days_ago = datetime.utcnow() - timedelta(days=5)
    result = await db.execute(
        select(JobListing)
        .where(
            and_(
                JobListing.user_id == user.id,
                JobListing.found_at >= five_days_ago,
                JobListing.is_active == True,
            )
        )
        .order_by(JobListing.match_score.desc().nullslast(), JobListing.found_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.get("/history", response_model=list[JobListingOut])
async def get_job_history(
    page: int = 1,
    per_page: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(JobListing)
        .where(JobListing.user_id == user.id)
        .order_by(JobListing.found_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    return result.scalars().all()


@router.post("/select")
async def select_jobs(
    req: JobSelectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for job_id in req.job_listing_ids:
        result = await db.execute(
            select(JobListing).where(
                and_(JobListing.id == job_id, JobListing.user_id == user.id)
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

        existing = await db.execute(
            select(UserJobSelection).where(
                and_(
                    UserJobSelection.user_id == user.id,
                    UserJobSelection.job_listing_id == job_id,
                )
            )
        )
        if not existing.scalar_one_or_none():
            db.add(UserJobSelection(user_id=user.id, job_listing_id=job_id))

    await db.commit()
    return {"message": f"{len(req.job_listing_ids)} jobs selected"}


@router.put("/{job_id}/outcome")
async def update_outcome(
    job_id: int,
    req: JobOutcomeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobListing).where(
            and_(JobListing.id == job_id, JobListing.user_id == user.id)
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        outcome_status = OutcomeStatus(req.status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    existing = await db.execute(
        select(JobOutcome).where(
            and_(JobOutcome.user_id == user.id, JobOutcome.job_listing_id == job_id)
        )
    )
    outcome = existing.scalar_one_or_none()
    if outcome:
        outcome.status = outcome_status
        outcome.updated_at = datetime.utcnow()
    else:
        db.add(JobOutcome(user_id=user.id, job_listing_id=job_id, status=outcome_status))

    await db.commit()
    return {"message": "Outcome updated"}
