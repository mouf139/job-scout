from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.search_criteria import SearchCriteria
from app.schemas.search_criteria import SearchCriteriaOut, SearchCriteriaUpdate
from app.services.auth import get_current_user

router = APIRouter()


@router.get("/criteria", response_model=SearchCriteriaOut | None)
async def get_criteria(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SearchCriteria).where(SearchCriteria.user_id == user.id)
    )
    return result.scalar_one_or_none()


@router.put("/criteria", response_model=SearchCriteriaOut)
async def update_criteria(
    req: SearchCriteriaUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SearchCriteria).where(SearchCriteria.user_id == user.id)
    )
    sc = result.scalar_one_or_none()

    update_data = req.model_dump(exclude_unset=True)
    if sc:
        for key, value in update_data.items():
            setattr(sc, key, value)
    else:
        sc = SearchCriteria(user_id=user.id, **update_data)
        db.add(sc)

    await db.commit()
    await db.refresh(sc)
    return sc


@router.get("/dashboard-stats")
async def dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.job_listing import JobListing
    from app.models.tailored_resume import TailoredResume
    from app.models.pipeline_run import PipelineRun
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    jobs_today = await db.execute(
        select(func.count(JobListing.id)).where(
            JobListing.user_id == user.id,
            JobListing.found_at >= today,
        )
    )
    resumes_total = await db.execute(
        select(func.count(TailoredResume.id)).where(TailoredResume.user_id == user.id)
    )
    last_run = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.user_id == user.id)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    run = last_run.scalar_one_or_none()

    return {
        "jobs_scanned_today": jobs_today.scalar() or 0,
        "resumes_generated": resumes_total.scalar() or 0,
        "pipeline_status": run.status if run else "never_run",
        "last_run": run.started_at if run else None,
    }


@router.get("/preference-profile")
async def get_preference_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.preference_profile import PreferenceProfile
    result = await db.execute(
        select(PreferenceProfile).where(PreferenceProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {"profile": None, "message": "Not enough data yet. Keep selecting jobs for 2+ weeks."}
    return {
        "profile": profile.profile_json,
        "last_updated": profile.last_updated,
    }


@router.post("/trigger-scan")
async def trigger_scan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.tasks.scan_jobs import scan_jobs_for_user
    result = await db.execute(
        select(SearchCriteria).where(SearchCriteria.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No search criteria set")
    scan_jobs_for_user.delay(user.id)
    return {"message": "Job scan triggered"}
