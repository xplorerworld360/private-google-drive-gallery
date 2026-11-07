import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

READONLY_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]

class DriveGallery:
    def __init__(self):
        try:
            info = dict(st.secrets["gdrive_service_account"])
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=READONLY_SCOPE
            )
            self.api = build("drive", "v3", credentials=credentials, cache_discovery=False)
            self.root_id = str(st.secrets["gdrive_root_folder_id"])
        except Exception as exc:
            raise RuntimeError(f"Google Drive credentials are not configured correctly: {exc}") from exc

    def _list(self, query):
        output, token = [], None
        try:
            while True:
                result = self.api.files().list(
                    q=query,
                    pageSize=1000,
                    pageToken=token,
                    orderBy="name",
                    fields="nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,webViewLink)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                ).execute()
                output.extend(result.get("files", []))
                token = result.get("nextPageToken")
                if not token:
                    return output
        except HttpError as exc:
            raise RuntimeError(f"Google Drive API error: {exc}") from exc

    def list_albums(self):
        query = (
            f"'{self.root_id}' in parents and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        return self._list(query)

    def list_images(self, album_id=None, query=""):
        parents = [album_id] if album_id else [a["id"] for a in self.list_albums()]
        images = []
        for parent in parents:
            q = f"'{parent}' in parents and mimeType contains 'image/' and trashed=false"
            if query:
                safe_query = query.replace("\\", "\\\\").replace("'", "\\'")
                q += f" and name contains '{safe_query}'"
            images.extend(self._list(q))
        return sorted(images, key=lambda x: x.get("name", "").lower())

    def download_bytes(self, file_id):
        try:
            request = self.api.files().get_media(fileId=file_id, supportsAllDrives=True)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except HttpError as exc:
            raise RuntimeError(f"Could not download image: {exc}") from exc
