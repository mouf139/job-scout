from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


def _get_drive_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("drive", "v3", credentials=creds)


def create_user_folder(user_name: str) -> dict:
    service = _get_drive_service()

    folder_metadata = {
        "name": f"Job Scout — {user_name}",
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=folder_metadata, fields="id,webViewLink").execute()

    return {
        "folder_id": folder["id"],
        "folder_url": folder["webViewLink"],
    }


def share_folder(folder_id: str, email: str):
    service = _get_drive_service()
    permission = {
        "type": "user",
        "role": "writer",
        "emailAddress": email,
    }
    service.permissions().create(
        fileId=folder_id,
        body=permission,
        sendNotificationEmail=True,
    ).execute()


def upload_file(folder_id: str, file_path: str, filename: str) -> dict:
    service = _get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
    media = MediaFileUpload(
        file_path,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,webViewLink",
    ).execute()

    return {
        "file_id": file["id"],
        "file_url": file["webViewLink"],
    }
