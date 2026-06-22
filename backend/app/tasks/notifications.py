import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
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


@celery.task(name="app.tasks.notifications.send_daily_digests")
def send_daily_digests():
    from app.models.user import User
    from app.models.search_criteria import SearchCriteria
    from app.models.job_listing import JobListing
    from app.services.email_service import send_daily_digest

    async def _send():
        session_factory = _make_session()
        async with session_factory() as db:
            result = await db.execute(
                select(User, SearchCriteria)
                .join(SearchCriteria, User.id == SearchCriteria.user_id)
                .where(
                    User.is_active == True,
                    User.onboarding_completed == True,
                    SearchCriteria.email_notifications_enabled == True,
                )
            )
            rows = result.all()

            for user, sc in rows:
                five_days_ago = datetime.utcnow() - timedelta(days=5)
                jobs_result = await db.execute(
                    select(JobListing)
                    .where(
                        JobListing.user_id == user.id,
                        JobListing.found_at >= five_days_ago,
                        JobListing.is_active == True,
                    )
                    .order_by(JobListing.match_score.desc().nullslast(), JobListing.found_at.desc())
                    .limit(10)
                )
                jobs = jobs_result.scalars().all()
                if not jobs:
                    continue

                jobs_data = [
                    {
                        "title": j.title,
                        "company": j.company,
                        "location": j.location,
                        "salary": j.salary,
                        "is_new": j.is_new,
                        "apply_options_json": j.apply_options_json,
                    }
                    for j in jobs
                ]

                try:
                    send_daily_digest(
                        user.name,
                        user.email,
                        jobs_data,
                        f"{settings.app_url}/dashboard",
                    )
                except Exception as e:
                    logger.error(f"Failed to send digest to {user.email}: {e}")

    _run_async(_send())


@celery.task(name="app.tasks.notifications.send_admin_daily")
def send_admin_daily():
    from app.models.user import User
    from app.models.pipeline_run import PipelineRun
    from app.services.email_service import send_admin_daily_report

    async def _send():
        session_factory = _make_session()
        async with session_factory() as db:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            users_result = await db.execute(
                select(User).where(User.is_active == True, User.onboarding_completed == True)
            )
            users = users_result.scalars().all()

            reports = []
            for user in users:
                run_result = await db.execute(
                    select(PipelineRun)
                    .where(PipelineRun.user_id == user.id, PipelineRun.started_at >= today)
                    .order_by(PipelineRun.started_at.desc())
                    .limit(1)
                )
                run = run_result.scalar_one_or_none()
                reports.append({
                    "user_name": user.name,
                    "status": run.status if run else "no_run",
                    "jobs_found": run.jobs_found if run else 0,
                    "resumes_generated": run.resumes_generated if run else 0,
                    "errors": run.errors if run else None,
                })

            if reports:
                send_admin_daily_report(reports)

    _run_async(_send())


@celery.task(name="app.tasks.notifications.update_feedback_profiles")
def update_feedback_profiles():
    from app.models.user import User
    from app.services.feedback import has_enough_data, generate_preference_profile

    async def _update():
        session_factory = _make_session()
        async with session_factory() as db:
            users_result = await db.execute(
                select(User).where(User.is_active == True, User.onboarding_completed == True)
            )
            for user in users_result.scalars().all():
                if await has_enough_data(user.id, db):
                    try:
                        await generate_preference_profile(user.id, db)
                        logger.info(f"Updated preference profile for user {user.id}")
                    except Exception as e:
                        logger.error(f"Feedback profile update failed for user {user.id}: {e}")

    _run_async(_update())
