import hashlib
import hmac
import json
import secrets
import time

import requests
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/drive",
]
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _settings():
    if "google_oauth" not in st.secrets:
        raise RuntimeError("Missing [google_oauth] section in Streamlit Cloud Secrets.")
    cfg = dict(st.secrets["google_oauth"])
    required = ("client_id", "client_secret", "redirect_uri")
    missing = [key for key in required if not cfg.get(key)]
    if missing:
        raise RuntimeError("Missing OAuth settings: " + ", ".join(missing))
    return cfg


def _client_config():
    cfg = _settings()
    return {"web": {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [cfg["redirect_uri"]],
    }}


def _make_state():
    cfg = _settings()
    payload = f"{int(time.time())}.{secrets.token_urlsafe(24)}"
    signature = hmac.new(cfg["client_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _verify_state(value):
    try:
        timestamp, nonce, signature = value.split(".", 2)
        if abs(time.time() - int(timestamp)) > 900:
            return False
        payload = f"{timestamp}.{nonce}"
        expected = hmac.new(_settings()["client_secret"].encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


def _nonce_from_state(value):
    try:
        timestamp, nonce, signature = value.split(".", 2)
        return nonce
    except Exception:
        return ""


def _make_flow(state=None):
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=state)
    flow.redirect_uri = _settings()["redirect_uri"]
    return flow


def _clear_user_state():
    keys = [
        "google_credentials_json", "google_user", "google_login_error",
        "drive_gallery_index", "drive_gallery_thumbnails", "gallery_root_by_user",
        "selected_folder_id", "gallery_favourites", "preview_item_id",
        "admin_selected_folder", "gallery_page", "gallery_filter_key",
        "gallery_index_loaded", "admin_media_page", "admin_filter_key",
        "bulk_select", "bulk_confirm", "clear_bulk_selection",
    ]
    for key in keys:
        st.session_state.pop(key, None)


def _callback():
    params = st.query_params
    oauth_error = params.get("error")
    if oauth_error:
        st.session_state["google_login_error"] = f"Google sign-in was not completed: {oauth_error}"
        params.clear()
        return

    code = params.get("code")
    state = params.get("state")
    if not code:
        return

    if not state or not _verify_state(state):
        st.session_state["google_login_error"] = "The sign-in response could not be verified. Please try again."
        params.clear()
        return

    try:
        flow = _make_flow(state=state)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Validate the OIDC ID token audience, issuer, expiry and nonce to protect the sign-in callback.
        from google.oauth2 import id_token as google_id_token
        claims = google_id_token.verify_oauth2_token(
            credentials.id_token,
            Request(),
            _settings()["client_id"],
        )
        if claims.get("nonce") != _nonce_from_state(state):
            raise RuntimeError("Google sign-in nonce validation failed.")

        user_response = requests.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=(10, 25),
        )
        user_response.raise_for_status()
        user_data = user_response.json()
        if not user_data.get("sub") or not user_data.get("email"):
            raise RuntimeError("Google did not return a valid account identity.")
        if user_data.get("email_verified") is False:
            raise RuntimeError("The Google account email is not verified.")
        if user_data.get("sub") != claims.get("sub"):
            raise RuntimeError("Google account identity verification failed.")

        # A new Google identity must never inherit the previous account's cached Drive data.
        old_user = st.session_state.get("google_user", {}).get("sub")
        old_credentials_json = st.session_state.get("google_credentials_json")
        if old_user and old_user != user_data["sub"]:
            _clear_user_state()
            old_credentials_json = None
        if not credentials.refresh_token and old_credentials_json and old_user == user_data["sub"]:
            try:
                previous_credentials = Credentials.from_authorized_user_info(
                    json.loads(old_credentials_json), scopes=SCOPES
                )
                credentials.refresh_token = previous_credentials.refresh_token
            except Exception:
                pass

        st.session_state["google_credentials_json"] = credentials.to_json()
        st.session_state["google_user"] = {
            "sub": user_data["sub"],
            "email": user_data["email"],
            "name": user_data.get("name") or user_data["email"].split("@")[0],
            "picture": user_data.get("picture", ""),
        }
        st.session_state.pop("google_login_error", None)
        params.clear()
        st.rerun()
    except Exception as exc:
        st.session_state["google_login_error"] = f"Google sign-in failed: {exc}"
        params.clear()


def _credentials():
    raw = st.session_state.get("google_credentials_json")
    if not raw:
        return None
    try:
        credentials = Credentials.from_authorized_user_info(json.loads(raw), scopes=SCOPES)
        if credentials.expired:
            if not credentials.refresh_token:
                raise RuntimeError("Google session expired. Sign in again.")
            credentials.refresh(Request())
            st.session_state["google_credentials_json"] = credentials.to_json()
        return credentials if credentials.valid else None
    except Exception as exc:
        _clear_user_state()
        st.session_state["google_login_error"] = str(exc)
        return None


def _login_screen():
    st.markdown("""
    <div class="login-card">
      <div class="eyebrow">PRIVATE PHOTO LIBRARY</div>
      <h1>Welcome to your gallery.</h1>
      <p>Sign in with Google to browse and manage your own Drive collection.</p>
      <div class="login-note">Each Google account gets its own gallery space. Uploads and admin actions are restricted to the signed-in account's gallery folder.</div>
    </div>
    """, unsafe_allow_html=True)
    if st.session_state.get("google_login_error"):
        st.error(st.session_state["google_login_error"])
    try:
        state = _make_state()
        flow = _make_flow(state=state)
        url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account consent",
            nonce=_nonce_from_state(state),
        )
        st.link_button("Continue with Google", url, type="primary", use_container_width=True)
    except Exception as exc:
        st.error(str(exc))


def require_google_user():
    try:
        _callback()
    except Exception as exc:
        st.session_state["google_login_error"] = str(exc)

    credentials = _credentials()
    user = st.session_state.get("google_user")
    if credentials and user:
        return credentials, user
    _login_screen()
    return None


def logout():
    _clear_user_state()
    st.rerun()
