import requests
import streamlit as st
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession, Request

READONLY_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]
FILES_URL = "https://www.googleapis.com/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"

def _session_for_token(token):
    session = requests.Session()
    retry = Retry(
        total=3, connect=3, read=2, status=3, backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]), raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session

@st.cache_data(ttl=600, max_entries=4000, show_spinner=False)
def _cached_list(parent_id, item_kind, access_token):
    q = (
        f"'{parent_id}' in parents and mimeType='{FOLDER_MIME}' and trashed=false"
        if item_kind == "folder"
        else f"'{parent_id}' in parents and mimeType contains 'image/' and trashed=false"
    )
    session = _session_for_token(access_token)
    output, token = [], None
    try:
        while True:
            params = {
                "q": q,
                "pageSize": 1000,
                "orderBy": "name",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,thumbnailLink,thumbnailVersion)",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if token:
                params["pageToken"] = token
            response = session.get(FILES_URL, params=params, timeout=(12, 45))
            response.raise_for_status()
            data = response.json()
            output.extend(data.get("files", []))
            token = data.get("nextPageToken")
            if not token:
                return output
    finally:
        session.close()

def _fetch_all_children(parent_id, access_token):
    """Fetch direct folders and images in one Drive list request per folder."""
    session = _session_for_token(access_token)
    output, token = [], None
    query = (
        f"'{parent_id}' in parents and trashed=false and "
        f"(mimeType='{FOLDER_MIME}' or mimeType contains 'image/')"
    )
    try:
        while True:
            params = {
                "q": query,
                "pageSize": 1000,
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,thumbnailLink,thumbnailVersion)",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if token:
                params["pageToken"] = token
            response = session.get(FILES_URL, params=params, timeout=(12, 45))
            response.raise_for_status()
            data = response.json()
            output.extend(data.get("files", []))
            token = data.get("nextPageToken")
            if not token:
                return output
    finally:
        session.close()

@st.cache_data(ttl=600, max_entries=50, show_spinner=False)
def _cached_gallery_index(root_folder_id, access_token):
    """
    One cached recursive index for the complete gallery.
    Folder levels are scanned in parallel; file metadata is indexed once and
    subsequent searches/folder navigation are local operations.
    """
    all_images = []
    folder_parent = {root_folder_id: None}
    visited = {root_folder_id}
    frontier = [root_folder_id]
    workers = 10

    while frontier:
        batch = frontier
        frontier = []
        with ThreadPoolExecutor(max_workers=min(workers, len(batch))) as pool:
            batch_results = list(pool.map(
                lambda folder_id: _fetch_all_children(folder_id, access_token),
                batch
            ))

        for parent_id, children in zip(batch, batch_results):
            for item in children:
                mime = item.get("mimeType", "")
                if mime == FOLDER_MIME:
                    folder_id = item["id"]
                    if folder_id not in visited:
                        visited.add(folder_id)
                        folder_parent[folder_id] = parent_id
                        frontier.append(folder_id)
                elif mime.startswith("image/"):
                    item["_gallery_parent_id"] = parent_id
                    all_images.append(item)

    all_images.sort(key=lambda item: item.get("name", "").casefold())
    return all_images, folder_parent

@lru_cache(maxsize=1200)
def _cached_thumbnail(thumbnail_url, access_token, thumbnail_version):
    # Bounded in-memory cache; thumbnailVersion invalidates a preview after file updates.
    if not thumbnail_url:
        return None
    session = _session_for_token(access_token)
    try:
        response = session.get(thumbnail_url, timeout=(8, 25))
        if response.status_code == 200:
            return response.content
        return None
    except requests.RequestException:
        return None
    finally:
        session.close()

class DriveGallery:
    """Google Drive read-only client with cached recursive index and cached thumbnails."""

    def __init__(self):
        info = dict(st.secrets["gdrive_service_account"])
        self.credentials = service_account.Credentials.from_service_account_info(
            info, scopes=READONLY_SCOPE
        )
        self.root_id = str(st.secrets["gdrive_root_folder_id"]).strip()
        if not self.root_id:
            raise ValueError("gdrive_root_folder_id is empty")
        self._authorized = AuthorizedSession(self.credentials)

    def _token(self):
        if not self.credentials.valid:
            self.credentials.refresh(Request())
        return self.credentials.token

    def list_folders(self, parent_id):
        return _cached_list(parent_id, "folder", self._token())

    def list_images_recursive(self, folder_id, query=""):
        # The complete tree is cached once. Folder selection and filename search do not call Drive again.
        all_images, folder_parent = _cached_gallery_index(self.root_id, self._token())
        children_by_parent = {}
        for child_id, parent_id in folder_parent.items():
            if parent_id is not None:
                children_by_parent.setdefault(parent_id, []).append(child_id)
        allowed = {folder_id}
        stack = [folder_id]
        while stack:
            parent = stack.pop()
            for child_id in children_by_parent.get(parent, []):
                if child_id not in allowed:
                    allowed.add(child_id)
                    stack.append(child_id)

        term = (query or "").casefold()
        return [
            item for item in all_images
            if item.get("_gallery_parent_id") in allowed
            and (not term or term in item.get("name", "").casefold())
        ]

    def get_thumbnail(self, item):
        version = item.get("thumbnailVersion") or item.get("modifiedTime", "")
        return _cached_thumbnail(item.get("thumbnailLink"), self._token(), version)

    def clear_thumbnail_cache(self):
        _cached_thumbnail.cache_clear()

    def download_bytes(self, file_id):
        response = self._authorized.get(
            f"{FILES_URL}/{file_id}",
            params={"alt": "media"},
            timeout=(15, 120),
            stream=True,
        )
        response.raise_for_status()
        chunks = []
        for chunk in response.iter_content(chunk_size=512 * 1024):
            if chunk:
                chunks.append(chunk)
        response.close()
        return b"".join(chunks)
