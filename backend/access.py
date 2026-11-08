import json
import re
import time
from datetime import datetime, timezone

import streamlit as st
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_email(email):
    return str(email or "").strip().lower()


def _valid_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))


class AccessControl:
    """Read/write a tiny JSON allow-list stored in the owner's Drive and editable by the service account."""

    def __init__(self):
        settings = dict(st.secrets.get("gallery", {}))
        self.owner_email = _normalize_email(settings.get("owner_email", ""))
        self.root_folder_id = str(settings.get("root_folder_id", "")).strip()
        self.registry_file_id = str(settings.get("access_registry_file_id", "")).strip()

        if not self.owner_email:
            raise RuntimeError("Set gallery.owner_email in Streamlit Secrets.")
        if not self.root_folder_id:
            raise RuntimeError("Set gallery.root_folder_id in Streamlit Secrets.")
        if not self.registry_file_id:
            raise RuntimeError("Set gallery.access_registry_file_id in Streamlit Secrets.")

        service_info = dict(st.secrets["gdrive_service_account"])
        credentials = service_account.Credentials.from_service_account_info(
            service_info,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        self.session = AuthorizedSession(credentials)

    def _request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (12, 45))
        response = self.session.request(method, url, **kwargs)
        if response.status_code >= 400:
            try:
                message = response.json().get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise RuntimeError(f"Google Drive API HTTP {response.status_code}: {message}")
        if not response.content:
            return {}
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type:
            return response.json()
        return response.content

    def is_owner(self, email):
        return _normalize_email(email) == self.owner_email

    def load_registry(self, force=False):
        cache = st.session_state.get("gallery_acl_cache")
        if not force and cache and time.time() - cache["at"] < 30:
            return cache["data"]

        content = self._request(
            "GET",
            f"{DRIVE_FILES_URL}/{self.registry_file_id}",
            params={"alt": "media"},
        )
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")
        if isinstance(content, dict):
            data = content
        else:
            data = json.loads(content or "{}")

        if not isinstance(data, dict) or not isinstance(data.get("users", {}), dict):
            raise RuntimeError("Access registry JSON must be an object with a 'users' object.")
        data.setdefault("users", {})
        st.session_state["gallery_acl_cache"] = {"at": time.time(), "data": data}
        return data

    def get_access(self, email):
        normalized = _normalize_email(email)
        if self.is_owner(normalized):
            return {
                "email": normalized,
                "role": "owner",
                "active": True,
                "can_view": True,
                "can_download": True,
                "can_manage_users": True,
            }

        registry = self.load_registry()
        record = registry["users"].get(normalized)
        if not record or not record.get("active", False):
            return None

        role = record.get("role", "viewer")
        if record.get("email", normalized).strip().lower() != normalized:
            return None
        role_map = {
            "viewer": (True, False, False),
            "downloader": (True, True, False),
            "access_admin": (True, True, True),
        }
        if role not in role_map:
            return None
        can_view, can_download, can_manage = role_map[role]
        return {
            **record,
            "email": normalized,
            "role": role,
            "active": True,
            "can_view": can_view,
            "can_download": can_download,
            "can_manage_users": can_manage,
        }

    def _assert_manager(self, actor_email):
        actor = self.get_access(actor_email)
        if not actor or not actor.get("can_manage_users"):
            raise PermissionError("You do not have permission to manage gallery access.")
        return actor

    def add_or_update_user(self, actor_email, target_email, role):
        actor = self._assert_manager(actor_email)
        email = _normalize_email(target_email)
        if not _valid_email(email):
            raise ValueError("Enter a valid Gmail address.")
        if not email.endswith("@gmail.com") and "@" not in email:
            raise ValueError("Enter a valid Google account email.")
        if self.is_owner(email):
            raise ValueError("The gallery owner already has full access.")
        allowed_roles = {"viewer", "downloader"}
        if actor["role"] == "owner":
            allowed_roles.add("access_admin")
        if role not in allowed_roles:
            raise PermissionError("You cannot grant that privilege.")

        registry = self.load_registry(force=True)
        old = registry["users"].get(email, {})
        if actor["role"] != "owner" and old.get("role") == "access_admin":
            raise PermissionError("Only the gallery owner can change another access administrator.")
        registry["users"][email] = {
            "email": email,
            "role": role,
            "active": True,
            "added_at": old.get("added_at", _now()),
            "added_by": old.get("added_by", _normalize_email(actor_email)),
            "updated_at": _now(),
            "updated_by": _normalize_email(actor_email),
        }
        self.save_registry(registry)
        return registry["users"][email]

    def set_user_active(self, actor_email, target_email, active):
        actor = self._assert_manager(actor_email)
        email = _normalize_email(target_email)
        if self.is_owner(email):
            raise ValueError("The gallery owner's access cannot be changed.")
        registry = self.load_registry(force=True)
        record = registry["users"].get(email)
        if not record:
            raise ValueError("User is not in the access registry.")
        if actor["role"] != "owner" and record.get("role") == "access_admin":
            raise PermissionError("Only the gallery owner can change another access administrator.")
        record["active"] = bool(active)
        record["updated_at"] = _now()
        record["updated_by"] = _normalize_email(actor_email)
        self.save_registry(registry)

    def remove_user_record(self, actor_email, target_email):
        actor = self._assert_manager(actor_email)
        email = _normalize_email(target_email)
        if self.is_owner(email):
            raise ValueError("The gallery owner cannot be removed.")
        registry = self.load_registry(force=True)
        record = registry["users"].get(email)
        if not record:
            return
        if actor["role"] != "owner" and record.get("role") == "access_admin":
            raise PermissionError("Only the gallery owner can remove an access administrator.")
        registry["users"].pop(email, None)
        self.save_registry(registry)

    def save_registry(self, registry):
        body = json.dumps(registry, indent=2, ensure_ascii=False).encode("utf-8")
        response = self.session.patch(
            f"{DRIVE_UPLOAD_URL}/{self.registry_file_id}",
            params={"uploadType": "media", "fields": "id,name,mimeType,modifiedTime"},
            data=body,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            timeout=(15, 60),
        )
        if response.status_code >= 400:
            try:
                message = response.json().get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise RuntimeError(
                f"Could not update the access registry (HTTP {response.status_code}): {message}. "
                "Check that the Service Account has Editor permission on the registry JSON file."
            )
        st.session_state["gallery_acl_cache"] = {"at": time.time(), "data": registry}
