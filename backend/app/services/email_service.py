import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)


def _get_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("gmail", "v1", credentials=creds)


def send_email(to_email: str, subject: str, html_body: str, attachments: list[dict] | None = None):
    if not settings.google_refresh_token:
        logger.warning("Gmail OAuth not configured, skipping email")
        return

    service = _get_gmail_service()

    msg = MIMEMultipart()
    msg["From"] = settings.admin_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    if attachments:
        for att in attachments:
            part = MIMEBase("application", "octet-stream")
            with open(att["path"], "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{att["filename"]}"')
            msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_daily_digest(user_name: str, user_email: str, jobs: list[dict], dashboard_url: str):
    job_rows = ""
    for job in jobs:
        label = '<span style="color:#22c55e;font-weight:bold">New</span>' if job.get("is_new") else '<span style="color:#9ca3af">Still Active</span>'
        apply_links = ""
        for opt in (job.get("apply_options_json") or []):
            if opt.get("link"):
                apply_links += f' <a href="{opt["link"]}" style="color:#2563eb;font-size:12px">{opt.get("title", "Apply")}</a>'

        job_rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #e5e7eb">
            <div style="font-weight:500">{job["title"]} {label}</div>
            <div style="color:#6b7280;font-size:14px">{job["company"]} &middot; {job.get("location", "")}</div>
            <div style="font-size:12px;color:#9ca3af">{job.get("salary", "")}</div>
            <div style="margin-top:4px">{apply_links}</div>
          </td>
        </tr>"""

    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
      <h2 style="color:#111827">Job Scout Daily Digest</h2>
      <p style="color:#6b7280">Hi {user_name}, here are today's top job matches:</p>
      <table style="width:100%;border-collapse:collapse">{job_rows}</table>
      <p style="margin-top:16px">
        <a href="{dashboard_url}" style="background:#111827;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:14px">
          View Dashboard
        </a>
      </p>
      <p style="color:#9ca3af;font-size:12px;margin-top:24px">
        You're receiving this because email notifications are enabled in your Job Scout settings.
      </p>
    </div>"""

    send_email(settings.admin_email, f"Job Scout — Daily Digest for {user_name}", html)


def send_admin_daily_report(user_reports: list[dict]):
    all_success = all(r["status"] == "success" for r in user_reports)
    status_emoji = "Success" if all_success else "Failed"
    subject = f"Job Scout — {'✅' if all_success else '❌'} {status_emoji}"

    rows = ""
    for r in user_reports:
        status_color = "#22c55e" if r["status"] == "success" else "#ef4444"
        rows += f"""
        <tr>
          <td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">{r["user_name"]}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;color:{status_color}">{r["status"]}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">{r.get("jobs_found", 0)}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #e5e7eb">{r.get("resumes_generated", 0)}</td>
          <td style="padding:6px 8px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#ef4444">{r.get("errors", "") or ""}</td>
        </tr>"""

    html = f"""
    <div style="font-family:sans-serif;max-width:700px;margin:0 auto">
      <h2 style="color:#111827">Job Scout — Pipeline Report</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead>
          <tr style="background:#f9fafb">
            <th style="text-align:left;padding:6px 8px">User</th>
            <th style="text-align:left;padding:6px 8px">Status</th>
            <th style="text-align:left;padding:6px 8px">Jobs</th>
            <th style="text-align:left;padding:6px 8px">Resumes</th>
            <th style="text-align:left;padding:6px 8px">Errors</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

    send_email(settings.admin_email, subject, html)


def send_admin_weekly_report(stats: dict):
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
      <h2 style="color:#111827">Job Scout — Weekly Summary</h2>
      <ul style="color:#374151;line-height:2">
        <li>Total jobs found: <strong>{stats.get("total_jobs", 0)}</strong></li>
        <li>Total resumes generated: <strong>{stats.get("total_resumes", 0)}</strong></li>
        <li>Active users: <strong>{stats.get("active_users", 0)}</strong></li>
        <li>Inactive users: <strong>{stats.get("inactive_users", 0)}</strong></li>
      </ul>
    </div>"""

    send_email(settings.admin_email, "Job Scout — Weekly Summary", html)
