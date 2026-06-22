import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
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


@celery.task(name="app.tasks.scan_jobs.check_scheduled_scans")
def check_scheduled_scans():
    from app.models.user import User
    from app.models.search_criteria import SearchCriteria

    async def _check():
        session_factory = _make_session()
        async with session_factory() as db:
            result = await db.execute(
                select(User).where(User.is_active == True, User.onboarding_completed == True)
            )
            users = result.scalars().all()
            for user in users:
                criteria = await db.execute(
                    select(SearchCriteria).where(SearchCriteria.user_id == user.id)
                )
                if criteria.scalar_one_or_none():
                    scan_jobs_for_user.delay(user.id)

    _run_async(_check())


@celery.task(name="app.tasks.scan_jobs.scan_jobs_for_user", bind=True, max_retries=3)
def scan_jobs_for_user(self, user_id: int):
    from app.models.user import User
    from app.models.search_criteria import SearchCriteria
    from app.models.job_listing import JobListing
    from app.models.pipeline_run import PipelineRun
    from app.services.job_scanner import search_jobs

    async def _scan():
        session_factory = _make_session()
        async with session_factory() as db:
            user = await db.get(User, user_id)
            if not user or not user.is_active:
                return

            criteria_result = await db.execute(
                select(SearchCriteria).where(SearchCriteria.user_id == user_id)
            )
            sc = criteria_result.scalar_one_or_none()
            if not sc:
                return

            run = PipelineRun(
                user_id=user_id,
                run_type="job_scan",
                status="running",
            )
            db.add(run)
            await db.commit()

            try:
                jobs = await search_jobs(
                    titles=sc.titles or [],
                    location=sc.location,
                    include_keywords=sc.include_keywords,
                    exclude_keywords=sc.exclude_keywords,
                    remote_preference=sc.remote_preference,
                    job_type=sc.job_type,
                    radius_miles=sc.radius_miles,
                )

                existing = await db.execute(
                    select(JobListing.title, JobListing.company).where(
                        JobListing.user_id == user_id
                    )
                )
                existing_keys = {
                    (r[0].lower().strip(), r[1].lower().strip())
                    for r in existing.all()
                }

                new_count = 0
                for job in jobs:
                    key = (job["title"].lower().strip(), job["company"].lower().strip())
                    if key in existing_keys:
                        continue

                    db.add(JobListing(
                        user_id=user_id,
                        title=job["title"],
                        company=job["company"],
                        location=job["location"],
                        salary=job.get("salary"),
                        posting_date=job.get("posting_date"),
                        description=job.get("description"),
                        apply_options_json=job.get("apply_options", []),
                        source=job.get("source", "google_jobs"),
                        is_new=True,
                    ))
                    new_count += 1

                run.status = "success"
                run.jobs_found = new_count
                run.completed_at = datetime.utcnow()
                await db.commit()

                logger.info(f"Scan complete for user {user_id}: {new_count} new jobs found")

            except Exception as e:
                run.status = "failed"
                run.errors = str(e)
                run.completed_at = datetime.utcnow()
                await db.commit()
                raise

    try:
        _run_async(_scan())
    except Exception as exc:
        self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
