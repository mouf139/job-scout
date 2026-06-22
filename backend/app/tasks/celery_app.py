from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "jobscout",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-scheduled-scans": {
            "task": "app.tasks.scan_jobs.check_scheduled_scans",
            "schedule": crontab(minute="*/15"),
        },
        "send-daily-digests": {
            "task": "app.tasks.notifications.send_daily_digests",
            "schedule": crontab(hour=8, minute=0),
        },
        "send-admin-daily-report": {
            "task": "app.tasks.notifications.send_admin_daily",
            "schedule": crontab(hour=20, minute=0),
        },
        "update-feedback-profiles": {
            "task": "app.tasks.notifications.update_feedback_profiles",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

celery.autodiscover_tasks(["app.tasks"])

import app.tasks.scan_jobs  # noqa: F401, E402
import app.tasks.generate_resumes  # noqa: F401, E402
import app.tasks.notifications  # noqa: F401, E402
