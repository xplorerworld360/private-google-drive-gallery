import secrets
import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES=["openid","email","https://www.googleapis.com/auth/drive"]

def _config():
    c=st.secrets["google_oauth"]
    return {"web":{"client_id":c["client_id"],"client_secret":c["client_secret"],
      "auth_uri":"https://accounts.google.com/o/oauth2/auth",
      "token_uri":"https://oauth2.googleapis.com/token","redirect_uris":[c["redirect_uri"]]}}

def _flow(state=None):
    f=Flow.from_client_config(_config(),scopes=SCOPES,state=state)
    f.redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
    return f

def get_credentials():
    code=st.query_params.get("code")
    state=st.query_params.get("state")
    if code and state and state==st.session_state.get("oauth_state"):
        f=_flow(state)
        f.fetch_token(code=code)
        c=f.credentials
        st.session_state["drive_token"]={"token":c.token,"refresh_token":c.refresh_token,
          "token_uri":c.token_uri,"client_id":c.client_id,"client_secret":c.client_secret,"scopes":SCOPES}
        try:
            import requests
            r=requests.get("https://www.googleapis.com/oauth2/v2/userinfo",
              headers={"Authorization":f"Bearer {c.token}"},timeout=10)
            st.session_state["email"]=r.json().get("email","Google account") if r.ok else "Google account"
        except Exception: st.session_state["email"]="Google account"
        st.session_state.pop("oauth_state",None)
        st.query_params.clear()
        st.rerun()
    data=st.session_state.get("drive_token")
    if not data: return None
    c=Credentials(**data)
    if c.expired and c.refresh_token:
        c.refresh(Request()); data["token"]=c.token; st.session_state["drive_token"]=data
    return c if c.valid else None

def login():
    st.title("🔐 Sign in to your gallery")
    st.write("Connect securely using your own Google account. No service account is used.")
    if "google_oauth" not in st.secrets:
        st.error("Add [google_oauth] credentials in Streamlit Secrets."); st.stop()
    if st.button("Continue with Google",type="primary"):
        state=secrets.token_urlsafe(24)
        f=_flow(state)
        url,_=f.authorization_url(access_type="offline",include_granted_scopes="true",prompt="consent")
        st.session_state["oauth_state"]=state
        st.link_button("Open Google sign-in",url)

def sidebar():
    with st.sidebar:
        st.markdown("### Your gallery")
        st.caption(st.session_state.get("email","Google account"))
        if st.button("Sign out",use_container_width=True):
            for k in ["drive_token","email","oauth_state"]: st.session_state.pop(k,None)
            st.rerun()
