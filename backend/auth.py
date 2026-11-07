import hmac
import streamlit as st

def require_login():
    """Single-password gate for this private gallery."""
    if "gallery_authenticated" not in st.session_state:
        st.session_state.gallery_authenticated = False
    if st.session_state.gallery_authenticated:
        with st.sidebar:
            st.caption("Private session active")
            if st.button("Log out", use_container_width=True):
                st.session_state.gallery_authenticated = False
                st.rerun()
        return
    st.markdown("""
<<<<<<< HEAD
    <div style="max-width:560px;margin:10vh auto 1rem;padding:2rem;border:1px solid #e5e5ea;border-radius:22px;background:#fff">
    <div style="font-size:.75rem;letter-spacing:.14em;color:#777;font-weight:700">PRIVATE PHOTOS</div>
    <h1 style="font-size:2.1rem;margin:.5rem 0;color:#1d1d1f">Welcome back.</h1>
    <p style="color:#6e6e73">Enter your gallery password to continue.</p></div>
=======
    <div style="max-width:620px;margin:8vh auto 1rem auto;padding:2rem;border:1px solid #ffffff20;border-radius:22px;background:linear-gradient(120deg,#626cff25,#23c6a015)">
      <div style="font-size:.8rem;letter-spacing:.15em;color:#aeb9d2;font-weight:700">PRIVATE ACCESS</div>
      <h1 style="font-size:2.2rem;margin:.5rem 0">Welcome to your gallery</h1>
      <p style="color:#aeb9cc">Enter your gallery password to browse your private collection.</p>
    </div>
>>>>>>> parent of 46b59fa (ssl)
    """, unsafe_allow_html=True)
    password=st.text_input("Gallery password",type="password",placeholder="Password")
    if st.button("Unlock Photos",type="primary",use_container_width=True):
        expected=str(st.secrets.get("gallery_password",""))
        if expected and hmac.compare_digest(password,expected):
            st.session_state.gallery_authenticated=True
            st.rerun()
        st.error("Incorrect password.")
    st.stop()
