import hmac
import streamlit as st

def require_login():
    """Simple single-owner password gate. Store the password in Streamlit secrets."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        with st.sidebar:
            st.success("Private session")
            if st.button("Log out"):
                st.session_state.authenticated = False
                st.rerun()
        return

    st.title("🔒 Private Gallery Login")
    st.caption("Sign in to view your Google Drive gallery.")
    password = st.text_input("Gallery password", type="password")
    if st.button("Sign in", type="primary"):
        expected = st.secrets.get("gallery_password", "")
        if expected and hmac.compare_digest(password, str(expected)):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
