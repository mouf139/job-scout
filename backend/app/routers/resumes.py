from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.job_listing import JobListing
from app.models.tailored_resume import TailoredResume
from app.models.user_job_selection import UserJobSelection
from app.schemas.job import JobSelectionRequest
from app.services.auth import get_current_user
from app.tasks.generate_resumes import generate_resume_for_job

router = APIRouter()


@router.post("/generate")
async def generate_resumes(
    req: JobSelectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_resume = await db.execute(
        select(Resume).where(Resume.user_id == user.id, Resume.is_base == True)
    )
    if not base_resume.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="No base resume uploaded. Complete onboarding first.")

    queued = 0
    for job_id in req.job_listing_ids:
        job = await db.execute(
            select(JobListing).where(
                and_(JobListing.id == job_id, JobListing.user_id == user.id)
            )
        )
        if not job.scalar_one_or_none():
            continue

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

        generate_resume_for_job.delay(user.id, job_id)
        queued += 1

    await db.commit()
    return {
        "message": f"Resume generation queued for {queued} jobs",
        "status": "queued",
        "count": queued,
    }


@router.get("/")
async def list_tailored_resumes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoredResume, JobListing)
        .join(JobListing, TailoredResume.job_listing_id == JobListing.id)
        .where(TailoredResume.user_id == user.id)
        .order_by(TailoredResume.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": tr.id,
            "job_listing_id": tr.job_listing_id,
            "job_title": jl.title,
            "company": jl.company,
            "google_drive_url": tr.google_drive_url,
            "created_at": tr.created_at,
        }
        for tr, jl in rows
    ]


@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoredResume).where(
            and_(TailoredResume.id == resume_id, TailoredResume.user_id == user.id)
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return FileResponse(
        resume.file_path,
        filename=f"resume_{resume.id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
