import asyncio
import logging
import os
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)


def _make_session():
    engine = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery.task(name="app.tasks.generate_resumes.generate_resume_for_job")
def generate_resume_for_job(user_id: int, job_listing_id: int):
    from app.models.resume import Resume
    from app.models.job_listing import JobListing
    from app.models.tailored_resume import TailoredResume
    from app.models.pipeline_run import PipelineRun
    from app.services.resume_tailor import tailor_resume, create_docx, sanitize_filename

    async def _generate():
        session_factory = _make_session()
        async with session_factory() as db:
            resume_result = await db.execute(
                select(Resume).where(Resume.user_id == user_id, Resume.is_base == True)
            )
            base_resume = resume_result.scalar_one_or_none()
            if not base_resume:
                logger.error(f"No base resume for user {user_id}")
                return

            job_result = await db.execute(
                select(JobListing).where(
                    and_(JobListing.id == job_listing_id, JobListing.user_id == user_id)
                )
            )
            job = job_result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_listing_id} not found for user {user_id}")
                return

            run = PipelineRun(
                user_id=user_id,
                run_type="resume_generation",
                status="running",
            )
            db.add(run)
            await db.commit()

            try:
                resume_data = await tailor_resume(
                    base_resume.file_path,
                    job.description or "",
                    job.title,
                    job.company,
                )

                filename = f"{sanitize_filename(job.company)}_{sanitize_filename(job.title)}.docx"
                output_dir = os.path.join(settings.upload_dir, str(user_id), "tailored")
                output_path = os.path.join(output_dir, filename)

                create_docx(resume_data, output_path)

                drive_url = None
                from app.models.user import User
                user = await db.get(User, user_id)
                if user and user.google_drive_folder_id and settings.google_refresh_token:
                    try:
                        from app.services.google_drive import upload_file
                        result = upload_file(user.google_drive_folder_id, output_path, filename)
                        drive_url = result["file_url"]
                    except Exception as e:
                        logger.error(f"Google Drive upload failed: {e}")

                tailored = TailoredResume(
                    user_id=user_id,
                    job_listing_id=job_listing_id,
                    file_path=output_path,
                    google_drive_url=drive_url,
                )
                db.add(tailored)

                run.status = "success"
                run.resumes_generated = 1
                run.completed_at = datetime.utcnow()
                await db.commit()

                logger.info(f"Resume generated for user {user_id}, job {job_listing_id}")

            except Exception as e:
                run.status = "failed"
                run.errors = str(e)
                run.completed_at = datetime.utcnow()
                await db.commit()
                logger.error(f"Resume generation failed: {e}")
                raise

    _run_async(_generate())
