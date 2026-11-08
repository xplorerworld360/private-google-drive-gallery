import streamlit as st
from backend.auth import require_login
from backend.drive import DriveGallery

st.set_page_config(
    page_title="My Private Gallery",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.block-container {max-width:1600px;padding-top:1.35rem;padding-bottom:3rem;}
[data-testid="stAppViewContainer"] {background:linear-gradient(145deg,#10131b 0%,#171d2a 55%,#11151e 100%);}
[data-testid="stHeader"] {background:transparent;}
h1,h2,h3 {font-family:'Manrope',sans-serif;letter-spacing:-.035em;}
section[data-testid="stSidebar"] {background:#111722;border-right:1px solid #ffffff12;}
.hero {padding:1.55rem 1.7rem;border:1px solid #ffffff18;border-radius:22px;background:linear-gradient(115deg,#626cff30,#23c6a018);margin-bottom:1.15rem;}
.eyebrow {font-size:.73rem;text-transform:uppercase;letter-spacing:.16em;color:#aeb9d2;font-weight:700;}
.hero-title {font-family:'Manrope',sans-serif;font-size:clamp(1.8rem,3vw,2.55rem);font-weight:800;line-height:1.12;margin:.4rem 0;}
.hero-sub {color:#b7c1d4;font-size:.95rem;max-width:760px;}
.metric {padding:1rem 1.1rem;border:1px solid #ffffff17;border-radius:16px;background:#ffffff08;min-height:88px;}
.metric-label {font-size:.72rem;letter-spacing:.09em;color:#aeb9cc;font-weight:700;}
.metric-value {font-family:'Manrope',sans-serif;font-size:1.45rem;font-weight:800;margin-top:.2rem;}
div[data-testid="stImage"] img {border-radius:14px;object-fit:cover;}
div.stButton > button, div.stDownloadButton > button {border-radius:11px;font-weight:600;}
div[data-testid="stTextInput"] input {border-radius:12px;}
div[data-testid="stSelectbox"] div[role="combobox"] {border-radius:12px;}
.muted {color:#aeb9cc;font-size:.84rem;}
.card-title {font-weight:700;overflow-wrap:anywhere;}
</style>
""", unsafe_allow_html=True)

require_login()

@st.cache_resource
def get_drive():
    return DriveGallery()

try:
    drive = get_drive()
    albums = drive.list_albums()
except Exception as exc:
    st.error(f"Unable to connect to Google Drive: {exc}")
    st.info("Check your service-account credentials and confirm the Drive folder is shared with the service-account email.")
    st.stop()

# Load image metadata once per run; image bytes are fetched only for visible cards.
all_images = drive.list_images()
total_bytes = sum(int(x.get("size", 0) or 0) for x in all_images)
total_mb = total_bytes / (1024 * 1024)

st.markdown("""
<div class="hero">
  <div class="eyebrow">A private space for your collection</div>
  <div class="hero-title">Your gallery, beautifully organised.</div>
  <div class="hero-sub">Explore your albums, search your collection and enjoy your images in a clean, modern gallery. Your originals stay in Google Drive.</div>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
for col, label, value in [
    (m1, "ALBUMS", len(albums)),
    (m2, "IMAGES", len(all_images)),
    (m3, "TOTAL IMAGE SIZE", f"{total_mb:.1f} MB"),
    (m4, "STORAGE", "Google Drive"),
]:
    with col:
        st.markdown(
            f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")
heading, count_col = st.columns([3, 1])
with heading:
    st.subheader("Explore your collection")
with count_col:
    st.markdown('<div class="muted" style="text-align:right;padding-top:14px">Private · Read-only gallery</div>', unsafe_allow_html=True)

albums_by_name = {a["name"]: a for a in albums}
album_options = ["All albums"] + sorted(albums_by_name.keys(), key=str.lower)

f1, f2, f3, f4 = st.columns([1.45, 2.2, 1.1, 1.1])
with f1:
    selected_album = st.selectbox("Album", album_options, label_visibility="collapsed")
with f2:
    search = st.text_input("Search", placeholder="⌕  Search by filename…", label_visibility="collapsed")
with f3:
    sort_by = st.selectbox("Sort", ["Newest first", "Oldest first", "Name A–Z", "Name Z–A"], label_visibility="collapsed")
with f4:
    layout = st.selectbox("Grid", ["Comfortable", "Compact"], label_visibility="collapsed")

album_id = None if selected_album == "All albums" else albums_by_name[selected_album]["id"]
images = drive.list_images(album_id=album_id, query=search.strip())

if sort_by == "Newest first":
    images.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
elif sort_by == "Oldest first":
    images.sort(key=lambda x: x.get("modifiedTime", ""))
elif sort_by == "Name A–Z":
    images.sort(key=lambda x: x.get("name", "").lower())
else:
    images.sort(key=lambda x: x.get("name", "").lower(), reverse=True)

# Session-only favourites; nothing is written to Drive.
if "favourites" not in st.session_state:
    st.session_state.favourites = set()

show_favourites = st.toggle("Show favourites only", value=False)
if show_favourites:
    images = [x for x in images if x["id"] in st.session_state.favourites]

page_size = 20
if "gallery_page" not in st.session_state:
    st.session_state.gallery_page = 1
max_pages = max(1, (len(images) + page_size - 1) // page_size)
st.session_state.gallery_page = min(st.session_state.gallery_page, max_pages)

if search or selected_album != "All albums" or show_favourites:
    st.session_state.gallery_page = 1

start = (st.session_state.gallery_page - 1) * page_size
visible = images[start:start + page_size]
st.caption(f"Showing {len(visible)} of {len(images)} image(s) · {selected_album}")

if not images:
    st.info("No images found. Add images or create album folders directly in your Google Drive, then refresh this page.")
else:
    ncols = 5 if layout == "Compact" else 4
    for row_start in range(0, len(visible), ncols):
        columns = st.columns(ncols, gap="medium")
        for col, item in zip(columns, visible[row_start:row_start+ncols]):
            with col:
                try:
                    data = drive.download_bytes(item["id"])
                    st.image(data, use_container_width=True)
                    name = item.get("name", "Untitled image")
                    st.markdown(f'<div class="card-title">{name}</div>', unsafe_allow_html=True)
                    size = int(item.get("size", 0) or 0)
                    date = item.get("modifiedTime", "")[:10]
                    st.caption(f"{date} · {size/1024:.0f} KB" if size else date)
                    fav = item["id"] in st.session_state.favourites
                    b1, b2 = st.columns([1, 1])
                    with b1:
                        if st.button("♥ Saved" if fav else "♡ Save", key=f"fav_{item['id']}", use_container_width=True):
                            if fav:
                                st.session_state.favourites.remove(item["id"])
                            else:
                                st.session_state.favourites.add(item["id"])
                            st.rerun()
                    with b2:
                        st.download_button(
                            "↓ Download",
                            data=data,
                            file_name=name,
                            mime=item.get("mimeType", "application/octet-stream"),
                            key=f"download_{item['id']}",
                            use_container_width=True,
                        )
                    if st.button("View image", key=f"view_{item['id']}", use_container_width=True):
                        st.session_state["selected_image"] = item["id"]
                        st.session_state["selected_image_name"] = name
                        st.rerun()
                except Exception as exc:
                    st.warning(f"Could not load {item.get('name', 'image')}: {exc}")

    if max_pages > 1:
        p1, p2, p3 = st.columns([1, 2, 1])
        with p1:
            if st.button("← Previous", disabled=st.session_state.gallery_page <= 1, use_container_width=True):
                st.session_state.gallery_page -= 1
                st.rerun()
        with p2:
            st.markdown(f"<div style='text-align:center;padding:.5rem'>Page {st.session_state.gallery_page} of {max_pages}</div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next →", disabled=st.session_state.gallery_page >= max_pages, use_container_width=True):
                st.session_state.gallery_page += 1
                st.rerun()

if st.session_state.get("selected_image"):
    selected_id = st.session_state["selected_image"]
    try:
        selected_data = drive.download_bytes(selected_id)
        st.divider()
        st.subheader(st.session_state.get("selected_image_name", "Image preview"))
        st.image(selected_data, use_container_width=True)
        if st.button("Close image viewer"):
            st.session_state.pop("selected_image", None)
            st.session_state.pop("selected_image_name", None)
            st.rerun()
    except Exception as exc:
        st.error(f"Unable to open image: {exc}")

with st.sidebar:
    st.markdown("## 🖼️ My Gallery")
    st.caption("Private Google Drive collection")
    st.divider()
    st.markdown("**Manage your collection**")
    st.write("Add, rename, move or delete images directly in Google Drive.")
    st.link_button("Open Google Drive", "https://drive.google.com/drive/my-drive", use_container_width=True)
    if st.button("Refresh gallery", use_container_width=True):
        st.rerun()
    st.divider()
    st.caption("The gallery is read-only. Changes made in Google Drive appear after refreshing.")
    st.caption("Your Drive files are not made public by this app.")
