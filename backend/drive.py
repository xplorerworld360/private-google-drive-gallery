import requests
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession, Request

FILES_URL = "https://www.googleapis.com/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"


def _http_session(token):
    session = requests.Session()
    retry = Retry(
        total=3, connect=3, read=2, status=3, backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]), raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def _list_folder_children(folder_id, token):
    session = _http_session(token)
    # Fetch direct children without MIME substring filters; Drive supports classification locally.
    query = f"'{folder_id}' in parents and trashed=false"
    result, page_token = [], None
    try:
        while True:
            params = {
                "q": query,
                "pageSize": 1000,
                "orderBy": "name",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,thumbnailLink,thumbnailVersion,webViewLink)",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if page_token:
                params["pageToken"] = page_token
            response = session.get(FILES_URL, params=params, timeout=(12, 45))
            response.raise_for_status()
            data = response.json()
            result.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return result
    finally:
        session.close()


@st.cache_data(ttl=600, max_entries=500, show_spinner=False)
def _cached_folder_children(folder_id, service_token):
    """Fetch only one folder's immediate children; nested folders load on demand."""
    return _list_folder_children(folder_id, service_token)


@st.cache_data(ttl=1800, max_entries=2500, show_spinner=False)
def _cached_thumbnail(url, token, thumbnail_version):
    if not url:
        return None
    session = _http_session(token)
    try:
        response = session.get(url, timeout=(8, 25))
        if response.status_code == 200:
            return response.content
        return None
    except requests.RequestException:
        return None
    finally:
        session.close()


class DriveGallery:
    def __init__(self):
        info = dict(st.secrets["gdrive_service_account"])
        self.credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        self.root_id = str(st.secrets["gallery"]["root_folder_id"]).strip()
        if not self.root_id:
            raise RuntimeError("gallery.root_folder_id is empty.")
        self.session = AuthorizedSession(self.credentials)

    def token(self):
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token

    def get_folder_children(self, folder_id, force=False):
        if force:
            _cached_folder_children.clear()
        return _cached_folder_children(str(folder_id), self.token())

    def invalidate_index(self):
        _cached_folder_children.clear()
        _cached_thumbnail.clear()

    def folder_items(self, folder_id, force=False):
        return self.get_folder_children(folder_id, force=force)

    def fetch_thumbnails(self, items, max_workers=12):
        token = self.token()
        def one(item):
            version = item.get("thumbnailVersion") or item.get("modifiedTime", "")
            return _cached_thumbnail(item.get("thumbnailLink", ""), token, version)
        with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(items)))) as pool:
            return list(pool.map(one, items))

    def download_bytes(self, item):
        # Verify the item is an immediate child of its claimed parent folder.
        parent_id = item.get("_gallery_parent_id") or (item.get("parents") or [None])[0]
        if not parent_id:
            raise PermissionError("This file is outside the configured gallery.")
        allowed = self.get_folder_children(parent_id)
        if not any(child.get("id") == item.get("id") and child.get("mimeType", "").startswith(("image/", "video/"))
                   for child in allowed):
            raise PermissionError("This file is outside the configured gallery.")
        response = self.session.get(
            f"{FILES_URL}/{item['id']}",
            params={"alt": "media"},
            timeout=(15, 180),
            stream=True,
        )
        response.raise_for_status()
        chunks = []
        for chunk in response.iter_content(chunk_size=512 * 1024):
            if chunk:
                chunks.append(chunk)
        response.close()
        return b"".join(chunks)
