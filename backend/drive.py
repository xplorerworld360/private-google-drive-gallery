import io
import json
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.auth.transport.requests import AuthorizedSession

FILES_URL = "https://www.googleapis.com/drive/v3/files"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"
APP_MARKER_KEY = "private_gallery_app"
APP_MARKER_VALUE = "personal_gallery_v1"


def _requests_session(token):
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST", "PATCH"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def _list_children_for_folder(folder_id, token):
    """Thread-local HTTP session; returns direct children only."""
    session = _requests_session(token)
    output, page_token = [], None
    query = (
        f"'{folder_id}' in parents and trashed=false and "
        f"(mimeType='{FOLDER_MIME}' or mimeType contains 'image/' or mimeType contains 'video/')"
    )
    try:
        while True:
            params = {
                "q": query,
                "pageSize": 1000,
                "orderBy": "name",
                "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,thumbnailLink,thumbnailVersion,webViewLink,ownedByMe,owners(emailAddress),trashed)",
                "corpora": "user",
            }
            if page_token:
                params["pageToken"] = page_token
            response = session.get(FILES_URL, params=params, timeout=(12, 45))
            if response.status_code >= 400:
                try:
                    message = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    message = response.text
                raise RuntimeError(f"Drive API HTTP {response.status_code}: {message}")
            data = response.json()
            output.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return output
    finally:
        session.close()


class DriveGallery:
    """Per-Google-user Drive client; all gallery/admin operations stay under that user's owned root."""

    def __init__(self, credentials, user):
        self.credentials = credentials
        self.user = user
        self.user_id = user["sub"]
        self.email = user["email"]
        self.session = AuthorizedSession(credentials)
        read_retry = Retry(
            total=3, connect=3, read=2, status=3, backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]), raise_on_status=False,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=read_retry, pool_connections=8, pool_maxsize=8))
        self.root_id = self._ensure_gallery_root()

    def _request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (12, 45))
        response = self.session.request(method, url, **kwargs)
        if response.status_code >= 400:
            try:
                message = response.json().get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise RuntimeError(f"Google Drive API HTTP {response.status_code}: {message}")
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def _get_file(self, file_id):
        return self._request(
            "GET",
            f"{FILES_URL}/{file_id}",
            params={"fields": "id,name,mimeType,ownedByMe,owners(emailAddress),parents,trashed,appProperties"},
        )

    def _ensure_gallery_root(self):
        # Keep the user's gallery root in their Streamlit session to avoid a Drive lookup on every rerun.
        root_cache = st.session_state.get("gallery_root_by_user", {})
        cached_root = root_cache.get(self.user_id)
        if cached_root:
            return cached_root

        # Optional migration path: reuse the old root only if the signed-in user owns it.
        legacy_id = ""
        try:
            legacy_id = str(
                __import__("streamlit").secrets.get(
                    "legacy_gallery_folder_id",
                    __import__("streamlit").secrets.get("gdrive_root_folder_id", ""),
                )
            ).strip()
        except Exception:
            legacy_id = ""

        if legacy_id:
            try:
                legacy = self._get_file(legacy_id)
                owners = [x.get("emailAddress", "").lower() for x in legacy.get("owners", [])]
                if (
                    legacy.get("mimeType") == FOLDER_MIME
                    and legacy.get("ownedByMe") is True
                    and (not owners or self.email.lower() in owners)
                    and not legacy.get("trashed", False)
                ):
                    root_cache[self.user_id] = legacy_id
                    st.session_state["gallery_root_by_user"] = root_cache
                    return legacy_id
            except Exception:
                pass

        # Otherwise find this app's marked folder in the signed-in user's My Drive.
        q = (
            f"appProperties has {{ key='{APP_MARKER_KEY}' and value='{APP_MARKER_VALUE}' }} "
            f"and mimeType='{FOLDER_MIME}' and 'root' in parents and trashed=false"
        )
        result = self._request(
            "GET", FILES_URL,
            params={
                "q": q, "pageSize": 100,
                "fields": "files(id,name,mimeType,ownedByMe,owners(emailAddress),appProperties)",
                "corpora": "user",
            },
        )
        for folder in result.get("files", []):
            owners = [x.get("emailAddress", "").lower() for x in folder.get("owners", [])]
            if folder.get("ownedByMe") is True and (not owners or self.email.lower() in owners):
                root_cache[self.user_id] = folder["id"]
                st.session_state["gallery_root_by_user"] = root_cache
                return folder["id"]

        created = self._request(
            "POST", FILES_URL,
            json={
                "name": "My Streamlit Gallery",
                "mimeType": FOLDER_MIME,
                "parents": ["root"],
                "appProperties": {APP_MARKER_KEY: APP_MARKER_VALUE},
            },
            params={"fields": "id,name,mimeType,ownedByMe,owners(emailAddress)"},
        )
        root_cache[self.user_id] = created["id"]
        st.session_state["gallery_root_by_user"] = root_cache
        return created["id"]

    def _get_access_token(self):
        if self.credentials.expired:
            from google.auth.transport.requests import Request
            self.credentials.refresh(Request())
        return self.credentials.token

    def get_index(self, force=False):
        key = "drive_gallery_index"
        now = time.time()
        cached = st_cache_get(key)
        if (
            not force
            and cached
            and cached.get("user_id") == self.user_id
            and cached.get("root_id") == self.root_id
            and now - cached.get("created_at", 0) < 600
        ):
            return cached

        token = self._get_access_token()
        folders_by_id = {
            self.root_id: {
                "id": self.root_id,
                "name": "My Streamlit Gallery",
                "mimeType": FOLDER_MIME,
                "ownedByMe": True,
                "parents": ["root"],
            }
        }
        media_by_id = {}
        folder_parent = {self.root_id: None}
        children_by_parent = {self.root_id: []}
        all_children_by_parent = {self.root_id: []}
        visited = {self.root_id}
        frontier = [self.root_id]

        while frontier:
            batch = frontier
            frontier = []
            with ThreadPoolExecutor(max_workers=min(10, len(batch))) as pool:
                child_batches = list(pool.map(lambda folder_id: _list_children_for_folder(folder_id, token), batch))

            for parent_id, child_items in zip(batch, child_batches):
                children_by_parent.setdefault(parent_id, [])
                all_children_by_parent.setdefault(parent_id, [])
                for item in child_items:
                    item["_gallery_parent_id"] = parent_id
                    all_children_by_parent[parent_id].append(item)
                    if item.get("ownedByMe") is not True:
                        continue
                    children_by_parent[parent_id].append(item)
                    if item.get("mimeType") == FOLDER_MIME:
                        folder_id = item["id"]
                        if folder_id not in visited:
                            visited.add(folder_id)
                            folders_by_id[folder_id] = item
                            folder_parent[folder_id] = parent_id
                            children_by_parent.setdefault(folder_id, [])
                            all_children_by_parent.setdefault(folder_id, [])
                            frontier.append(folder_id)
                    elif item.get("mimeType", "").startswith(("image/", "video/")):
                        media_by_id[item["id"]] = item

        cached = {
            "user_id": self.user_id,
            "root_id": self.root_id,
            "created_at": now,
            "folders_by_id": folders_by_id,
            "media_by_id": media_by_id,
            "folder_parent": folder_parent,
            "children_by_parent": children_by_parent,
            "all_children_by_parent": all_children_by_parent,
            "media": list(media_by_id.values()),
        }
        st_cache_set(key, cached)
        return cached

    def invalidate_index(self):
        st_cache_delete("drive_gallery_index")
        st_cache_delete("drive_gallery_thumbnails")

    def list_descendant_folder_ids(self, folder_id, index=None):
        index = index or self.get_index()
        children_by_parent = index["children_by_parent"]
        found = {folder_id}
        stack = [folder_id]
        while stack:
            parent = stack.pop()
            for item in children_by_parent.get(parent, []):
                if item.get("mimeType") == FOLDER_MIME and item["id"] not in found:
                    found.add(item["id"])
                    stack.append(item["id"])
        return found

    def media_in_folder(self, folder_id, recursive=True):
        index = self.get_index()
        allowed = self.list_descendant_folder_ids(folder_id, index) if recursive else {folder_id}
        return [
            item for item in index["media"]
            if item.get("_gallery_parent_id") in allowed
        ]

    def children_folders(self, folder_id):
        index = self.get_index()
        return [
            item for item in index["children_by_parent"].get(folder_id, [])
            if item.get("mimeType") == FOLDER_MIME
        ]

    def _thumbnail_cache(self):
        return st_cache_get("drive_gallery_thumbnails") or {}

    def fetch_thumbnails(self, items, max_workers=12):
        cache = self._thumbnail_cache()
        token = self._get_access_token()
        results = [None] * len(items)
        missing = []
        for i, item in enumerate(items):
            cache_key = (item["id"], item.get("thumbnailVersion") or item.get("modifiedTime", ""))
            if cache_key in cache:
                results[i] = cache[cache_key]
            else:
                missing.append((i, item, cache_key))

        def fetch_one(entry):
            i, item, cache_key = entry
            url = item.get("thumbnailLink")
            if not url:
                return i, cache_key, None
            session = _requests_session(token)
            try:
                response = session.get(url, timeout=(8, 25))
                if response.status_code == 200:
                    return i, cache_key, response.content
                return i, cache_key, None
            except requests.RequestException:
                return i, cache_key, None
            finally:
                session.close()

        if missing:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(missing))) as pool:
                for i, cache_key, content in pool.map(fetch_one, missing):
                    results[i] = content
                    if content:
                        cache[cache_key] = content

        # Bound the session cache to prevent memory growing without limit.
        if len(cache) > 500:
            cache = dict(list(cache.items())[-500:])
        st_cache_set("drive_gallery_thumbnails", cache)
        return results


    def _folder_is_within_gallery(self, folder_id):
        """Check live Drive ancestry; do not trust a potentially stale cached index."""
        if folder_id == self.root_id:
            return True
        current_id = folder_id
        visited = set()
        for _ in range(30):
            if current_id == self.root_id:
                return True
            if not current_id or current_id in visited:
                return False
            visited.add(current_id)
            try:
                meta = self._get_file(current_id)
            except Exception:
                return False
            if meta.get("mimeType") != FOLDER_MIME or meta.get("ownedByMe") is not True:
                return False
            parents = meta.get("parents") or []
            if self.root_id in parents:
                return True
            if not parents:
                return False
            current_id = parents[0]
        return False

    def _assert_folder(self, folder_id):
        if folder_id == self.root_id:
            return {
                "id": self.root_id,
                "name": "My Streamlit Gallery",
                "mimeType": FOLDER_MIME,
                "ownedByMe": True,
                "parents": ["root"],
            }
        meta = self._get_file(folder_id)
        if meta.get("mimeType") != FOLDER_MIME or meta.get("ownedByMe") is not True:
            raise PermissionError("This destination folder is not owned by the signed-in Google user.")
        if not self._folder_is_within_gallery(folder_id):
            raise PermissionError("This destination folder is outside the signed-in user's gallery.")
        return meta

    def _assert_media(self, file_id):
        meta = self._get_file(file_id)
        mime = meta.get("mimeType", "")
        if not mime.startswith(("image/", "video/")):
            raise PermissionError("This is not a supported gallery media file.")
        if meta.get("ownedByMe") is not True:
            raise PermissionError("This media is not owned by the signed-in Google user.")
        parents = meta.get("parents") or []
        if not parents or not self._folder_is_within_gallery(parents[0]):
            raise PermissionError("This media is outside the signed-in user's gallery.")
        return meta

    def _folder_has_children_live(self, folder_id):
        result = self._request(
            "GET", FILES_URL,
            params={
                "q": f"'{folder_id}' in parents and trashed=false",
                "pageSize": 1,
                "fields": "files(id)",
                "corpora": "user",
            },
        )
        return bool(result.get("files", []))

    def download_bytes(self, file_id):
        self._assert_media(file_id)
        response = self.session.get(
            f"{FILES_URL}/{file_id}",
            params={"alt": "media"},
            timeout=(15, 180),
            stream=True,
        )
        if response.status_code >= 400:
            response.raise_for_status()
        chunks = []
        for chunk in response.iter_content(chunk_size=512 * 1024):
            if chunk:
                chunks.append(chunk)
        response.close()
        return b"".join(chunks)

    def create_folder(self, name, parent_id):
        self._assert_folder(parent_id)
        clean = name.strip()
        if not clean:
            raise ValueError("Folder name cannot be empty.")
        result = self._request(
            "POST", FILES_URL,
            json={"name": clean, "mimeType": FOLDER_MIME, "parents": [parent_id]},
            params={"fields": "id,name,mimeType,parents,ownedByMe"},
        )
        self.invalidate_index()
        return result

    def upload_file(self, parent_id, filename, content, mime_type, invalidate=True):
        """Upload a file using Drive's resumable upload protocol."""
        self._assert_folder(parent_id)
        mime_type = mime_type or "application/octet-stream"
        init_response = self.session.post(
            UPLOAD_URL,
            params={
                "uploadType": "resumable",
                "fields": "id,name,mimeType,size,parents,modifiedTime,ownedByMe,thumbnailLink,thumbnailVersion",
            },
            json={"name": filename, "parents": [parent_id]},
            headers={
                "X-Upload-Content-Type": mime_type,
                "X-Upload-Content-Length": str(len(content)),
            },
            timeout=(20, 60),
        )
        if init_response.status_code >= 400:
            try:
                message = init_response.json().get("error", {}).get("message", init_response.text)
            except Exception:
                message = init_response.text
            raise RuntimeError(f"Could not start upload (HTTP {init_response.status_code}): {message}")

        upload_uri = init_response.headers.get("Location")
        if not upload_uri:
            raise RuntimeError("Google Drive did not return a resumable upload URL.")

        upload_response = self.session.put(
            upload_uri,
            data=content,
            headers={"Content-Type": mime_type, "Content-Length": str(len(content))},
            timeout=(20, 300),
        )
        if upload_response.status_code >= 400:
            try:
                message = upload_response.json().get("error", {}).get("message", upload_response.text)
            except Exception:
                message = upload_response.text
            raise RuntimeError(f"Upload failed (HTTP {upload_response.status_code}): {message}")
        result = upload_response.json()
        if invalidate:
            self.invalidate_index()
        return result

    def rename_item(self, file_id, new_name):
        if file_id == self.root_id:
            raise PermissionError("The gallery root cannot be renamed here.")
        meta = self._get_file(file_id)
        if meta.get("mimeType") == FOLDER_MIME:
            self._assert_folder(file_id)
        else:
            self._assert_media(file_id)
        if not new_name.strip():
            raise ValueError("Name cannot be empty.")
        result = self._request(
            "PATCH", f"{FILES_URL}/{file_id}",
            json={"name": new_name.strip()},
            params={"fields": "id,name,mimeType,parents"},
        )
        self.invalidate_index()
        return result

    def move_media(self, file_id, destination_folder_id):
        item = self._assert_media(file_id)
        self._assert_folder(destination_folder_id)
        old_parents = item.get("parents", [])
        if not old_parents:
            raise RuntimeError("Could not determine the current parent folder.")
        result = self._request(
            "PATCH", f"{FILES_URL}/{file_id}",
            params={
                "addParents": destination_folder_id,
                "removeParents": old_parents[0],
                "fields": "id,name,parents",
            },
            json={},
        )
        self.invalidate_index()
        return result

    def trash_item(self, file_id, invalidate=True):
        if file_id == self.root_id:
            raise PermissionError("The gallery root cannot be deleted.")
        meta = self._get_file(file_id)
        if meta.get("mimeType") == FOLDER_MIME:
            self._assert_folder(file_id)
            if self._folder_has_children_live(file_id):
                raise ValueError("This album is not empty. Move or trash its contents first.")
        else:
            self._assert_media(file_id)
        result = self._request(
            "PATCH", f"{FILES_URL}/{file_id}",
            json={"trashed": True},
            params={"fields": "id,name,trashed"},
        )
        if invalidate:
            self.invalidate_index()
        return result


# Session-state helpers avoid cross-user global caches.
def st_cache_get(key):
    return st.session_state.get(key)

def st_cache_set(key, value):
    st.session_state[key] = value

def st_cache_delete(key):
    st.session_state.pop(key, None)
