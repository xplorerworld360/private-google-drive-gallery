import streamlit as st
from backend.auth import logout

LIGHT = """
:root{color-scheme:light;--bg:#f4f8ff;--surface:rgba(255,255,255,.76);--solid:#fff;--surface2:#eaf2ff;--text:#10233f;--muted:#5f7190;--border:rgba(89,137,210,.19);--accent:#1769e8;--accent2:#5ba8ff;--shadow:0 12px 35px rgba(37,94,170,.09)}
"""
DARK = """
:root{color-scheme:dark;--bg:#091321;--surface:rgba(18,35,58,.84);--solid:#12233a;--surface2:#1a3556;--text:#f1f6ff;--muted:#a6bad6;--border:rgba(117,169,240,.2);--accent:#8db9ff;--accent2:#55a6ff;--shadow:0 12px 35px rgba(0,0,0,.24)}
"""

def apply_theme():
    if "gallery_theme" not in st.session_state:
        st.session_state.gallery_theme = "Light"
    palette = LIGHT if st.session_state.gallery_theme == "Light" else DARK
    st.markdown(f"""
    <style>
    {palette}
    [data-testid="stAppViewContainer"]{{background:radial-gradient(ellipse at 12% 0%,color-mix(in srgb,var(--accent2) 13%,var(--bg)),var(--bg) 58%);color:var(--text)}}
    [data-testid="stHeader"]{{background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(20px)}}
    .block-container{{max-width:1740px;padding:1.15rem 1.7rem 3rem}}
    section[data-testid="stSidebar"]{{background:color-mix(in srgb,var(--surface) 92%,var(--bg));backdrop-filter:blur(25px);border-right:1px solid var(--border)}}
    h1,h2,h3,h4,p,span,label,small,li{{color:var(--text)}}
    .eyebrow{{font-size:.68rem;letter-spacing:.16em;color:var(--accent);font-weight:800;text-transform:uppercase}}
    .subtle,.muted{{color:var(--muted);font-size:.9rem}}
    .glass-hero{{padding:1.45rem 1.65rem;border:1px solid var(--border);border-radius:24px;background:linear-gradient(120deg,var(--surface),color-mix(in srgb,var(--accent2) 8%,var(--surface)));box-shadow:var(--shadow);backdrop-filter:blur(22px);margin:.35rem 0 1.15rem}}
    .hero-title{{font-size:clamp(1.8rem,3vw,2.55rem);font-weight:800;letter-spacing:-.055em;line-height:1.08;margin:.38rem 0;color:var(--text)}}
    .hero-copy{{font-size:.92rem;color:var(--muted)}}
    .login-shell{{max-width:670px;margin:8vh auto 1rem;padding:2.3rem;border:1px solid var(--border);border-radius:28px;background:var(--surface);box-shadow:var(--shadow);backdrop-filter:blur(26px)}}
    .login-brand{{font-weight:850;letter-spacing:.18em;color:var(--accent);font-size:.78rem}}
    .login-eyebrow{{font-size:.7rem;color:var(--muted);letter-spacing:.16em;margin-top:2.3rem;font-weight:800}}
    .login-shell h1{{font-size:clamp(2rem,5vw,3.4rem);line-height:1.02;letter-spacing:-.06em;margin:.6rem 0;color:var(--text)}}
    .login-shell p{{font-size:1rem;color:var(--muted);max-width:500px}}
    .access-denied{{max-width:680px;margin:8vh auto 1rem;padding:2.2rem;border:1px solid var(--border);border-radius:24px;background:var(--surface);box-shadow:var(--shadow)}}
    .access-denied h1{{font-size:2.2rem;color:var(--text)}}
    .media-name{{font-size:.78rem;font-weight:650;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:.35rem 0}}
    .media-placeholder{{height:145px;background:var(--surface2);border:1px solid var(--border);border-radius:14px;display:grid;place-items:center;color:var(--muted);font-size:.78rem;font-weight:750}}
    .page-indicator{{text-align:center;padding:.55rem;color:var(--muted)}}
    div[data-testid="stTextInput"] input,div[data-testid="stSelectbox"] div[role="combobox"],div[data-testid="stMultiSelect"] div[role="combobox"]{{border-radius:12px;background:var(--solid);border-color:var(--border);color:var(--text)}}
    div[data-testid="stTextArea"] textarea{{background:var(--solid);color:var(--text);border-color:var(--border)}}
    div.stButton>button,div.stDownloadButton>button,div[data-testid="stLinkButton"] a{{border-radius:12px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-weight:650;backdrop-filter:blur(14px)}}
    div.stButton>button:hover,div.stDownloadButton>button:hover{{border-color:var(--accent);color:var(--accent);background:var(--surface2)}}
    [data-testid="stMetric"]{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:12px 15px;box-shadow:var(--shadow)}}
    [data-testid="stMetricLabel"],[data-testid="stMetricValue"]{{color:var(--text)}}
    div[data-testid="stImage"] img{{border-radius:14px;box-shadow:0 4px 15px rgba(20,55,100,.08)}}
    div[data-testid="stAlert"]{{border-radius:14px}}
    div[data-testid="stTabs"] button{{color:var(--muted)}}
    div[data-testid="stTabs"] button[aria-selected="true"]{{color:var(--accent)}}
    [data-testid="stExpander"]{{border-color:var(--border);border-radius:14px;background:var(--surface)}}
    [data-testid="stFileUploader"] section{{background:var(--surface);border:1px dashed var(--border);border-radius:14px}}
    [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"],[role="option"]{{background:var(--solid);color:var(--text)}}
    [data-testid="stCaptionContainer"] p{{color:var(--muted)}}
    </style>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### Appearance")
        st.radio("Theme", ["Light", "Dark"], horizontal=True, key="gallery_theme", label_visibility="collapsed")
        st.divider()


def render_account_sidebar(user):
    with st.sidebar:
        st.markdown("### Your account")
        st.markdown(f"**{user.get('name', 'Google user')}**")
        st.caption(user["email"])
        role_label = {
            "owner": "Gallery owner",
            "access_admin": "Access administrator",
            "downloader": "Viewer · Downloads enabled",
            "viewer": "Viewer · View only",
        }.get(user.get("role"), "Gallery user")
        st.caption(role_label)
        st.divider()
        if st.button("Sign out", use_container_width=True):
            logout()
        st.caption("This app only shares the gallery. All original files remain in the owner's Google Drive.")
