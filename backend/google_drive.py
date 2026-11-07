import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/drive"]

class DriveError(RuntimeError):
    pass

class DriveGallery:
    def __init__(self):
        try:
            info = dict(st.secrets["gdrive_service_account"])
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            self.service = build("drive", "v3", credentials=creds, cache_discovery=False)
            self.root_id = str(st.secrets["gdrive_root_folder_id"])
        except Exception as exc:
            raise DriveError(f"Invalid Google Drive configuration: {exc}") from exc

    def _list(self, q, fields="files(id,name,mimeType,modifiedTime,size)"):
        try:
            result, token = [], None
            while True:
                response = self.service.files().list(
                    q=q,
                    pageSize=1000,
                    pageToken=token,
                    orderBy="name",
                    fields=f"nextPageToken,{fields}",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                ).execute()
                result.extend(response.get("files", []))
                token = response.get("nextPageToken")
                if not token:
                    break
            return result
        except HttpError as exc:
            raise DriveError(f"Google Drive API error: {exc}") from exc

    def list_albums(self):
        q = (
            f"'{self.root_id}' in parents and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        return self._list(q)

    def list_images(self, album_id=None, query=""):
        parents = [album_id] if album_id else [a["id"] for a in self.list_albums()]
        files = []
        for parent in parents:
            q = f"'{parent}' in parents and mimeType contains 'image/' and trashed=false"
            if query:
                safe = query.replace("\\", "\\\\").replace("'", "\\'")
                q += f" and name contains '{safe}'"
            files.extend(self._list(q))
        files.sort(key=lambda x: x.get("name", "").lower())
        return files

    def download_bytes(self, file_id):
        try:
            request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except HttpError as exc:
            raise DriveError(f"Could not download file: {exc}") from exc

    def upload_file(self, album_id, filename, content, mime_type):
        try:
            media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)
            return self.service.files().create(
                body={"name": filename, "parents": [album_id]},
                media_body=media,
                fields="id,name",
                supportsAllDrives=True,
            ).execute()
        except HttpError as exc:
            raise DriveError(f"Could not upload file: {exc}") from exc

    def create_album(self, name):
        try:
            return self.service.files().create(
                body={
                    "name": name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [self.root_id],
                },
                fields="id,name",
                supportsAllDrives=True,
            ).execute()
        except HttpError as exc:
            raise DriveError(f"Could not create album: {exc}") from exc

    def delete_file(self, file_id):
        try:
            self.service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        except HttpError as exc:
            raise DriveError(f"Could not delete file: {exc}") from exc
