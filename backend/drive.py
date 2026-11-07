import io
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

READONLY_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"

class DriveGallery:
    """Read-only Drive client using Requests-based OAuth transport with retries."""

    def __init__(self):
        try:
            info = dict(st.secrets["gdrive_service_account"])
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=READONLY_SCOPE
            )
            self.session = AuthorizedSession(credentials)

            retry = Retry(
                total=4,
                connect=4,
                read=3,
                status=3,
                backoff_factor=1.0,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)
            self.root_id = str(st.secrets["gdrive_root_folder_id"]).strip()
            if not self.root_id:
                raise ValueError("gdrive_root_folder_id is empty")
        except Exception as exc:
            raise RuntimeError(f"Could not initialize Google Drive credentials: {exc}") from exc

    def _get(self, url, *, params=None, stream=False):
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=(15, 90),
                stream=stream,
            )
            if response.status_code >= 400:
                try:
                    detail = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    detail = response.text
                raise RuntimeError(f"Google Drive API returned HTTP {response.status_code}: {detail}")
            return response
        except requests.exceptions.SSLError as exc:
            raise RuntimeError(
                "TLS/SSL connection to Google failed after retries. "
                "The app now uses Requests + certifi and retries; if this persists, "
                "reboot Streamlit Cloud and verify its Python runtime/network. "
                f"Underlying SSL error: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Network error connecting to Google Drive after retries: {exc}") from exc

    def _list(self, query):
        output = []
        page_token = None
        while True:
            params = {
                "q": query,
                "pageSize": 1000,
                "orderBy": "name",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,webViewLink)",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if page_token:
                params["pageToken"] = page_token
            response = self._get(DRIVE_FILES_URL, params=params)
            data = response.json()
            output.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return output

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
                safe = query.replace("\\", "\\\\").replace("'", "\\'")
                q += f" and name contains '{safe}'"
            images.extend(self._list(q))
        return sorted(images, key=lambda x: x.get("name", "").casefold())

    def download_bytes(self, file_id):
        url = f"{DRIVE_FILES_URL}/{file_id}"
        response = self._get(url, params={"alt": "media"}, stream=True)
        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if chunk:
                buffer.write(chunk)
        response.close()
        return buffer.getvalue()
