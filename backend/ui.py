import streamlit as st
from backend.auth import logout

LIGHT_CSS = """
:root{color-scheme:light;--bg:#f5f5f7;--surface:#ffffff;--surface2:#f0f0f4;--text:#1d1d1f;--muted:#6e6e73;--border:#e4e4e9;--accent:#1677ff;--shadow:0 4px 18px #00000008}
"""
DARK_CSS = """
:root{color-scheme:dark;--bg:#0c1019;--surface:#151c29;--surface2:#202a3a;--text:#f4f6fb;--muted:#a6b1c4;--border:#2b3548;--accent:#9bb0ff;--shadow:0 6px 20px #00000028}
"""

def apply_theme():
    if "gallery_theme" not in st.session_state:
        st.session_state.gallery_theme = "Light"

    with st.sidebar:
        st.markdown("### Appearance")
        st.radio("Theme", ["Light", "Dark"], horizontal=True, key="gallery_theme", label_visibility="collapsed")

    theme = st.session_state.gallery_theme
    palette = LIGHT_CSS if theme == "Light" else DARK_CSS
    st.markdown(f"""
    <style>
    {palette}
    html,body,[data-testid="stAppViewContainer"]{{background:var(--bg);color:var(--text)}}
    [data-testid="stHeader"]{{background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(18px)}}
    .block-container{{max-width:1750px;padding:1.2rem 2rem 3rem}}
    section[data-testid="stSidebar"]{{background:var(--surface);border-right:1px solid var(--border)}}
    h1,h2,h3,h4,p,span,label,small,li{{color:var(--text)}}
    .eyebrow{{font-size:.68rem;letter-spacing:.15em;color:var(--muted);font-weight:800;text-transform:uppercase}}
    .hero-panel{{padding:1.35rem 1.55rem;margin:.2rem 0 1rem;border:1px solid var(--border);border-radius:20px;background:linear-gradient(115deg,var(--surface),var(--surface2));box-shadow:var(--shadow)}}
    .hero-heading{{font-size:clamp(1.8rem,3vw,2.45rem);font-weight:800;letter-spacing:-.055em;line-height:1.08;margin:.35rem 0;color:var(--text)}}
    .hero-copy{{font-size:.92rem;color:var(--muted)}}
    .subtle,.muted{{color:var(--muted);font-size:.9rem}}
    .media-name{{font-size:.78rem;font-weight:650;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:.35rem 0}}
    .media-placeholder{{height:145px;background:var(--surface2);border:1px solid var(--border);border-radius:12px;display:grid;place-items:center;color:var(--muted);font-size:.78rem;font-weight:700}}
    .page-indicator{{text-align:center;padding:.55rem;color:var(--muted)}}
    .login-card{{max-width:620px;margin:8vh auto 1rem;padding:2.1rem;border:1px solid var(--border);border-radius:24px;background:var(--surface);box-shadow:var(--shadow)}}
    .login-card h1{{font-size:2.2rem;margin:.55rem 0;color:var(--text)}}
    .login-card p{{color:var(--muted)}}
    .login-note{{padding:1rem;border-radius:14px;background:var(--surface2);color:var(--muted);font-size:.86rem;margin-top:1rem}}
    div[data-testid="stTextInput"] input,div[data-testid="stSelectbox"] div[role="combobox"],div[data-testid="stMultiSelect"] div[role="combobox"]{{border-radius:11px;background:var(--surface);border-color:var(--border);color:var(--text)}}
    div[data-testid="stTextArea"] textarea{{background:var(--surface);color:var(--text);border-color:var(--border)}}
    div.stButton>button,div.stDownloadButton>button,div[data-testid="stLinkButton"] a{{border-radius:11px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-weight:600}}
    div.stButton>button:hover,div.stDownloadButton>button:hover{{border-color:var(--accent);color:var(--accent)}}
    [data-testid="stMetric"]{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:12px 15px;box-shadow:var(--shadow)}}
    [data-testid="stMetricLabel"],[data-testid="stMetricValue"]{{color:var(--text)}}
    div[data-testid="stImage"] img{{border-radius:12px}}
    div[data-testid="stAlert"]{{border-radius:13px}}
    div[data-testid="stTabs"] button{{color:var(--muted)}}
    div[data-testid="stTabs"] button[aria-selected="true"]{{color:var(--accent)}}
    div[data-testid="stPopover"] button{{border-radius:10px}}
    [data-baseweb="popover"],[data-baseweb="menu"]{{background:var(--surface);color:var(--text)}}
    [data-testid="stExpander"]{{border-color:var(--border);border-radius:12px;background:var(--surface)}}
    [data-testid="stFileUploader"] section{{background:var(--surface);border:1px dashed var(--border);border-radius:14px}}
    [data-testid="stFileUploaderDropzone"]{{background:var(--surface);color:var(--text)}}
    [data-testid="stDataFrame"],[data-testid="stTable"]{{background:var(--surface);color:var(--text)}}
    [data-baseweb="select"]>div{{background:var(--surface);color:var(--text);border-color:var(--border)}}
    [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"]{{background:var(--surface);color:var(--text)}}
    [role="option"]{{background:var(--surface);color:var(--text)}}
    [role="option"]:hover{{background:var(--surface2)}}
    [data-testid="stWidgetLabel"]{{color:var(--muted)}}
    [data-testid="stCaptionContainer"] p{{color:var(--muted)}}
    [data-testid="stMarkdownContainer"]{{color:var(--text)}}
    [data-testid="stFileUploader"] section{{background:var(--surface);border:1px dashed var(--border);border-radius:14px}}
    [data-testid="stFileUploaderDropzone"]{{background:var(--surface);color:var(--text)}}
    input,textarea,button,select{{color-scheme:inherit}}
    ::placeholder{{color:var(--muted)!important;opacity:.8}}
    </style>
    """, unsafe_allow_html=True)
    return theme


def render_sidebar(user, active="gallery", theme=None):
    with st.sidebar:
        st.markdown("---")
        st.markdown("## ✦ My Gallery")
        st.caption(user.get("name") or user["email"])
        st.caption(user["email"])
        st.page_link("app.py", label="Photos", icon="🖼️")
        st.page_link("pages/1_Admin.py", label="Admin Studio", icon="⚙️")
        st.markdown("---")
        if st.button("Sign out", use_container_width=True):
            logout()
        st.caption("Your signed-in account has its own gallery space.")
