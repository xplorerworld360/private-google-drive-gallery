import streamlit as st

from backend.auth import require_google_user, logout
from backend.access import AccessControl
from backend.ui import apply_theme, render_account_sidebar

st.set_page_config(
    page_title="Blueglass Gallery",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
user = require_google_user()
if not user:
    st.stop()

try:
    access = AccessControl()
    role_record = access.get_access(user["email"])
except Exception as exc:
    st.error("The gallery access registry could not be read.")
    st.exception(exc)
    st.info("Ask the owner to verify the access registry file ID and share that JSON file with the Service Account as Editor.")
    st.stop()

if not role_record or not role_record.get("active", False):
    st.markdown("""
    <div class="access-denied">
      <div class="eyebrow">ACCESS NOT GRANTED</div>
      <h1>This gallery is private.</h1>
      <p>Your Google account is signed in, but it has not been granted gallery access yet.</p>
    </div>
    """, unsafe_allow_html=True)
    st.write(f"Signed in as **{user['email']}**")
    st.info("Contact the gallery owner and ask them to add your Gmail address in Access Management.")
    if st.button("Sign out"):
        logout()
    st.stop()

role = role_record["role"]
user_context = {**user, **role_record}
st.session_state["gallery_user"] = user_context

render_account_sidebar(user_context)

pages = [
    st.Page("pages/1_Gallery.py", title="Gallery", icon=":material/photo_library:", default=True),
]
if role in ("owner", "access_admin"):
    pages.append(st.Page("pages/2_Access_Admin.py", title="Access Management", icon=":material/manage_accounts:"))

navigation = st.navigation(pages, position="sidebar")
navigation.run()
