import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


async def search_jobs(
    titles: list[str],
    location: str | None = None,
    include_keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
    remote_preference: str | None = None,
    job_type: str | None = None,
    radius_miles: int | None = None,
) -> list[dict]:
    if not settings.serpapi_key:
        logger.warning("SERPAPI_KEY not configured, skipping job search")
        return []

    all_jobs = []

    for title in titles[:5]:
        query = title

        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": settings.serpapi_key,
        }

        # Only set location for non-remote searches with a real location
        if location and remote_preference != "remote":
            loc = location.strip()
            if loc.lower() not in ("remote", "anywhere", ""):
                params["location"] = loc

        chip_parts = []
        if job_type:
            type_map = {
                "full_time": "FULLTIME",
                "part_time": "PARTTIME",
                "internship": "INTERN",
                "contract": "CONTRACTOR",
            }
            mapped = type_map.get(job_type)
            if mapped:
                chip_parts.append(f"employment_type:{mapped}")

        chip_parts.append("date_posted:today")

        if chip_parts:
            params["chips"] = ",".join(chip_parts)

        if radius_miles and "location" in params:
            params["lrad"] = str(radius_miles)

        try:
            async with httpx.AsyncClient(timeout=30) as http_client:
                resp = await http_client.get(SERPAPI_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            jobs_results = data.get("jobs_results", [])
            for job in jobs_results:
                apply_options = []
                for opt in job.get("apply_options", []):
                    apply_options.append({
                        "title": opt.get("title", ""),
                        "link": opt.get("link", ""),
                        "source": opt.get("title", ""),
                    })

                detected_extensions = job.get("detected_extensions", {})

                all_jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "location": job.get("location", ""),
                    "salary": detected_extensions.get("salary", job.get("salary", "")),
                    "posting_date": _parse_posted_at(detected_extensions.get("posted_at", "")),
                    "description": job.get("description", ""),
                    "apply_options": apply_options,
                    "source": "google_jobs",
                })

        except Exception as e:
            logger.error(f"SerpAPI search failed for title '{title}': {e}")
            continue

    # Deduplicate by title + company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs[:20]


def _parse_posted_at(posted_at: str) -> datetime | None:
    if not posted_at:
        return None
    now = datetime.utcnow()
    posted_lower = posted_at.lower()
    if "hour" in posted_lower:
        try:
            hours = int("".join(c for c in posted_lower if c.isdigit()) or "1")
            return now - timedelta(hours=hours)
        except ValueError:
            return now
    elif "day" in posted_lower:
        try:
            days = int("".join(c for c in posted_lower if c.isdigit()) or "1")
            return now - timedelta(days=days)
        except ValueError:
            return now - timedelta(days=1)
    elif "just" in posted_lower or "today" in posted_lower:
        return now
    return None
