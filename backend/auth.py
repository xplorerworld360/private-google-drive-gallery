import hashlib
import hmac
import secrets
import time

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

IDENTITY_SCOPES = ["openid", "email", "profile"]


def _oauth_settings():
    if "google_oauth" not in st.secrets:
        raise RuntimeError("Missing [google_oauth] section in Streamlit Secrets.")
    settings = dict(st.secrets["google_oauth"])
    missing = [key for key in ("client_id", "client_secret", "redirect_uri") if not settings.get(key)]
    if missing:
        raise RuntimeError("Missing Google OAuth values: " + ", ".join(missing))
    return settings


def _client_config():
    settings = _oauth_settings()
    return {
        "web": {
            "client_id": settings["client_id"],
            "client_secret": settings["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings["redirect_uri"]],
        }
    }


def _make_state_and_nonce():
    settings = _oauth_settings()
    nonce = secrets.token_urlsafe(24)
    stamp = str(int(time.time()))
    payload = f"{stamp}.{nonce}"
    signature = hmac.new(
        settings["client_secret"].encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}", nonce


def _verify_state(state):
    try:
        stamp, nonce, signature = state.split(".", 2)
        if abs(time.time() - int(stamp)) > 900:
            return None
        payload = f"{stamp}.{nonce}"
        expected = hmac.new(
            _oauth_settings()["client_secret"].encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        return nonce
    except Exception:
        return None


def _flow(state=None):
    settings = _oauth_settings()
    flow = Flow.from_client_config(
        _client_config(),
        scopes=IDENTITY_SCOPES,
        state=state,
        autogenerate_code_verifier=True,
    )
    flow.redirect_uri = settings["redirect_uri"]
    return flow


def _clear_login_state():
    for key in (
        "gallery_google_user",
        "gallery_oauth_code_verifier",
        "gallery_google_login_error",
        "gallery_access_record",
        "gallery_user",
        "gallery_acl_cache",
        "gallery_index",
        "gallery_thumbnail_cache",
        "gallery_selected_folder",
        "gallery_favourites",
    ):
        st.session_state.pop(key, None)


def _handle_callback():
    params = st.query_params
    oauth_error = params.get("error")
    if oauth_error:
        st.session_state["gallery_google_login_error"] = f"Google sign-in was not completed: {oauth_error}"
        params.clear()
        return

    code = params.get("code")
    state = params.get("state")
    if not code:
        return

    nonce = _verify_state(str(state or ""))
    if not nonce:
        st.session_state["gallery_google_login_error"] = "Google sign-in could not be verified. Please try again."
        params.clear()
        return

    try:
        flow = _flow(state=state)
        # PKCE: the verifier generated before redirect must be restored
        # into the callback Flow before exchanging Google's authorization code.
        code_verifier = st.session_state.pop("gallery_oauth_code_verifier", None)
        if not code_verifier:
            raise RuntimeError("The sign-in session expired or its PKCE verifier was lost. Please try signing in again.")
        flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        token = flow.credentials.id_token
        if not token:
            raise RuntimeError("Google did not return an OpenID identity token.")

        claims = id_token.verify_oauth2_token(
            token,
            Request(),
            _oauth_settings()["client_id"],
        )
        if claims.get("nonce") != nonce:
            raise RuntimeError("Google sign-in nonce validation failed.")
        if not claims.get("sub") or not claims.get("email"):
            raise RuntimeError("Google did not return a valid Gmail identity.")
        if claims.get("email_verified") is not True:
            raise RuntimeError("Please use a Google account with a verified email address.")

        st.session_state["gallery_google_user"] = {
            "sub": claims["sub"],
            "email": claims["email"].strip().lower(),
            "name": claims.get("name") or claims["email"].split("@")[0],
            "picture": claims.get("picture", ""),
        }
        st.session_state.pop("gallery_google_login_error", None)
        params.clear()
        st.rerun()
    except Exception as exc:
        st.session_state["gallery_google_login_error"] = f"Google sign-in failed: {exc}"
        params.clear()


def require_google_user():
    try:
        _handle_callback()
    except Exception as exc:
        st.session_state["gallery_google_login_error"] = str(exc)

    user = st.session_state.get("gallery_google_user")
    if user:
        return user

    st.markdown("""
    <div class="login-shell">
      <div class="login-brand">✦ BLUEGLASS</div>
      <div class="login-eyebrow">YOUR PRIVATE PHOTO SPACE</div>
      <h1>Memories, beautifully gathered.</h1>
      <p>Sign in with your own Google account. The gallery owner controls who can view and download the collection.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("gallery_google_login_error"):
        st.error(st.session_state["gallery_google_login_error"])

    try:
        state, nonce = _make_state_and_nonce()
        flow = _flow(state=state)
        auth_url, _ = flow.authorization_url(
            access_type="online",
            include_granted_scopes="true",
            prompt="select_account",
            nonce=nonce,
        )
        # Save the PKCE verifier in this Streamlit browser session so it
        # survives the round-trip to Google and can be used in _handle_callback.
        st.session_state["gallery_oauth_code_verifier"] = flow.code_verifier
        st.link_button("Continue with Google", auth_url, type="primary", use_container_width=True)
        st.caption("Google shares your verified email and basic profile with this app. Your Google Drive is not connected to the visitor's account.")
    except Exception as exc:
        st.error(str(exc))
    return None


def logout():
    _clear_login_state()
    st.rerun()
