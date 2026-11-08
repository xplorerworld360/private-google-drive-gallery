from concurrent.futures import ThreadPoolExecutor
import math
import streamlit as st

from backend.auth import require_login
from backend.drive import DriveGallery

st.set_page_config(
    page_title="Photos",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
[data-testid="stAppViewContainer"]{background:#f5f5f7;color:#1d1d1f}
[data-testid="stHeader"]{background:rgba(245,245,247,.88);backdrop-filter:blur(18px)}
.block-container{max-width:1750px;padding:1.2rem 2rem 2.6rem}
section[data-testid="stSidebar"]{background:#fbfbfd;border-right:1px solid #e7e7eb}
section[data-testid="stSidebar"] *{color:#252529}
h1,h2,h3{color:#1d1d1f;font-family:Inter,sans-serif;letter-spacing:-.04em}
h1{font-weight:800}
div[data-testid="stTextInput"] input,div[data-testid="stSelectbox"] div[role="combobox"]{border-radius:12px;background:white;border-color:#e3e3e8}
div.stButton>button,div.stDownloadButton>button{border-radius:10px}
div[data-testid="stImage"] img{border-radius:12px}
.topline{font-size:.72rem;letter-spacing:.13em;color:#86868b;font-weight:750;text-transform:uppercase}
.subtitle{color:#6e6e73;font-size:.92rem}
.section-title{font-size:1.05rem;font-weight:750;letter-spacing:-.025em;color:#1d1d1f}
div[data-testid="stHorizontalBlock"]{gap:.7rem}
[data-testid="stMetric"]{background:white;border:1px solid #ececf0;border-radius:14px;padding:12px 15px}
div[data-testid="stAlert"]{border-radius:13px}
</style>
""", unsafe_allow_html=True)

require_login()

@st.cache_resource
def get_drive():
    return DriveGallery()

try:
    drive = get_drive()
except Exception as exc:
    st.error("Google Drive connection failed.")
    st.code(str(exc))
    st.info("Check your Service Account credentials in Streamlit Secrets and make sure the root folder is shared with the Service Account email as Viewer.")
    if st.button("Retry connection"):
        st.rerun()
    st.stop()

# Folder navigation state.
root_id = drive.root_id
if "folder_id" not in st.session_state:
    st.session_state.folder_id = root_id
if "folder_name" not in st.session_state:
    st.session_state.folder_name = "All Photos"
if "folder_path" not in st.session_state:
    st.session_state.folder_path = []

current_id = st.session_state.folder_id
current_name = st.session_state.folder_name
is_root = current_id == root_id

# Sidebar contains navigation only; no extra admin module.
with st.sidebar:
    st.markdown("## Photos")
    st.caption("Your private Google Drive library")
    st.divider()
    if st.button("▦  All Photos", use_container_width=True, type="primary" if is_root else "secondary"):
        st.session_state.folder_id = root_id
        st.session_state.folder_name = "All Photos"
        st.session_state.folder_path = []
        st.rerun()
    st.markdown("**Albums**")
    try:
        root_folders = drive.list_folders(root_id)
        for folder in root_folders:
            if st.button(("▣  " if current_id == folder["id"] else "▢  ") + folder["name"],
                         key=f"nav_{folder['id']}", use_container_width=True):
                st.session_state.folder_id = folder["id"]
                st.session_state.folder_name = folder["name"]
                st.session_state.folder_path = [{"id": folder["id"], "name": folder["name"]}]
                st.rerun()
    except Exception as exc:
        st.caption(f"Folders unavailable: {exc}")
    st.divider()
    if st.button("↻  Refresh library", use_container_width=True):
        st.cache_data.clear()
        # Backward-compatible: older DriveGallery modules may not expose this method.
        clear_thumbnails = getattr(drive, "clear_thumbnail_cache", None)
        if callable(clear_thumbnails):
            clear_thumbnails()
        st.rerun()
    st.link_button("Open Google Drive ↗", "https://drive.google.com/drive/my-drive", use_container_width=True)
    st.caption("Add, move or delete images directly in Google Drive.")

st.markdown('<div class="topline">YOUR LIBRARY</div>', unsafe_allow_html=True)
st.title("All Photos" if is_root else current_name)
if is_root:
    st.markdown('<div class="subtitle">All photos from your root folder and nested albums.</div>', unsafe_allow_html=True)
else:
    breadcrumb = ["All Photos"] + [x["name"] for x in st.session_state.folder_path]
    st.markdown('<div class="subtitle">' + " / ".join(breadcrumb) + '</div>', unsafe_allow_html=True)
    if st.button("← Back to All Photos"):
        st.session_state.folder_id = root_id
        st.session_state.folder_name = "All Photos"
        st.session_state.folder_path = []
        st.rerun()

# Controls are light, compact and server-side searchable.
c1, c2, c3, c4 = st.columns([2.2, 1.0, 1.0, 1.0])
with c1:
    search = st.text_input("Search", placeholder="Search your photos by filename…", label_visibility="collapsed")
with c2:
    sort = st.selectbox("Sort", ["Newest first", "Oldest first", "Name A–Z", "Name Z–A"], label_visibility="collapsed")
with c3:
    density = st.selectbox("Grid", ["Comfortable", "Dense"], label_visibility="collapsed")
with c4:
    scope = st.selectbox("Search scope", ["This album", "All Photos"], label_visibility="collapsed")

target_id = root_id if scope == "All Photos" else current_id

try:
    with st.spinner("Reading your library…" if "metadata_loaded" not in st.session_state else ""):
        # Metadata is cached for 10 minutes. Root collection recursively includes subfolders.
        images = drive.list_images_recursive(target_id, query=search.strip())
        folders = drive.list_folders(current_id)
except Exception as exc:
    st.error(f"Could not read your Drive library: {exc}")
    st.stop()

if sort == "Newest first":
    images.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
elif sort == "Oldest first":
    images.sort(key=lambda x: x.get("modifiedTime", ""))
elif sort == "Name A–Z":
    images.sort(key=lambda x: x.get("name", "").casefold())
else:
    images.sort(key=lambda x: x.get("name", "").casefold(), reverse=True)

# Favourites are retained for this browser session.
if "favourites" not in st.session_state:
    st.session_state.favourites = set()
show_favourites = st.toggle("Show favourites only", value=False)
if show_favourites:
    images = [x for x in images if x["id"] in st.session_state.favourites]

# Album folders are separate from image tiles.
if folders and scope == "This album" and not search:
    st.markdown('<div class="section-title">Albums</div>', unsafe_allow_html=True)
    folder_cols = st.columns(5)
    for i, folder in enumerate(folders):
        with folder_cols[i % len(folder_cols)]:
            with st.container(border=True):
                st.markdown(f"📁 **{folder['name']}**")
                st.caption("Open folder")
                if st.button("Open →", key=f"open_{folder['id']}", use_container_width=True):
                    st.session_state.folder_id = folder["id"]
                    st.session_state.folder_name = folder["name"]
                    st.session_state.folder_path = st.session_state.folder_path + [{"id": folder["id"], "name": folder["name"]}]
                    st.rerun()

st.markdown(f'<div class="section-title">Photos <span style="color:#86868b;font-weight:500">· {len(images)}</span></div>',
            unsafe_allow_html=True)

# 60 image metadata records per page; only small Drive thumbnails are fetched for visible tiles.
PAGE_SIZE = 60
page_count = max(1, math.ceil(len(images) / PAGE_SIZE))
if "gallery_page" not in st.session_state:
    st.session_state.gallery_page = 1
filter_key = (target_id, current_id, search, sort, density, show_favourites)
if st.session_state.get("gallery_filter_key") != filter_key:
    st.session_state.gallery_filter_key = filter_key
    st.session_state.gallery_page = 1
st.session_state.gallery_page = min(st.session_state.gallery_page, page_count)
offset = (st.session_state.gallery_page - 1) * PAGE_SIZE
visible = images[offset:offset + PAGE_SIZE]

# Thumbnail downloads run in parallel; cached thumbnails are reused across Streamlit reruns.
if visible:
    with st.spinner("Loading photo previews…" if "metadata_loaded" not in st.session_state else ""):
        with ThreadPoolExecutor(max_workers=10) as executor:
            thumbs = list(executor.map(drive.get_thumbnail, visible))
    st.session_state.metadata_loaded = True

    columns_per_row = 7 if density == "Dense" else 5
    for row_start in range(0, len(visible), columns_per_row):
        row_items = visible[row_start:row_start + columns_per_row]
        row_thumbs = thumbs[row_start:row_start + columns_per_row]
        cols = st.columns(columns_per_row, gap="small")
        for col, item, thumb in zip(cols, row_items, row_thumbs):
            with col:
                if thumb:
                    st.image(thumb, use_container_width=True)
                else:
                    st.markdown(
                        '<div style="height:130px;border-radius:12px;background:#e8e8ed;display:grid;place-items:center;color:#8e8e93">Preview unavailable</div>',
                        unsafe_allow_html=True,
                    )
                name = item.get("name", "Photo")
                st.caption(name)
                star_col, open_col = st.columns([1, 1])
                is_fav = item["id"] in st.session_state.favourites
                with star_col:
                    if st.button("★" if is_fav else "☆", key=f"star_{item['id']}", help="Favourite", use_container_width=True):
                        if is_fav:
                            st.session_state.favourites.remove(item["id"])
                        else:
                            st.session_state.favourites.add(item["id"])
                        st.rerun()
                with open_col:
                    if st.button("Open", key=f"open_photo_{item['id']}", use_container_width=True):
                        st.session_state.selected_photo_id = item["id"]
                        st.session_state.selected_photo_name = name
                        st.rerun()
else:
    st.info("No photos found. Add images to Google Drive or choose another album.")

# Full-resolution bytes are fetched only when the user opens a single photo.
if st.session_state.get("selected_photo_id"):
    selected_id = st.session_state.selected_photo_id
    selected_item = next((x for x in images if x["id"] == selected_id), None)
    if selected_item is None:
        st.session_state.pop("selected_photo_id", None)
        st.session_state.pop("selected_photo_name", None)
    else:
        @st.dialog("Photo preview", width="large")
        def photo_dialog(item):
            try:
                original = drive.download_bytes(item["id"])
                st.image(original, use_container_width=True)
                st.markdown(f"**{item.get('name', 'Photo')}**")
                left, mid, right = st.columns([1, 1, 1])
                with left:
                    st.download_button("Download original", original, file_name=item.get("name", "photo"), mime=item.get("mimeType", "application/octet-stream"), use_container_width=True)
                with mid:
                    if st.button("Previous", use_container_width=True):
                        idx = next((i for i, x in enumerate(images) if x["id"] == item["id"]), 0)
                        st.session_state.selected_photo_id = images[(idx - 1) % len(images)]["id"]
                        st.rerun()
                with right:
                    if st.button("Next", use_container_width=True):
                        idx = next((i for i, x in enumerate(images) if x["id"] == item["id"]), 0)
                        st.session_state.selected_photo_id = images[(idx + 1) % len(images)]["id"]
                        st.rerun()
            except Exception as exc:
                st.error(f"Could not open original image: {exc}")
            if st.button("Close viewer"):
                st.session_state.pop("selected_photo_id", None)
                st.session_state.pop("selected_photo_name", None)
                st.rerun()
        photo_dialog(selected_item)

if page_count > 1:
    a, b, c = st.columns([1, 2, 1])
    with a:
        if st.button("← Previous", disabled=st.session_state.gallery_page <= 1, use_container_width=True):
            st.session_state.gallery_page -= 1
            st.rerun()
    with b:
        st.markdown(f"<div style='text-align:center;padding:.5rem;color:#777'>Page {st.session_state.gallery_page} of {page_count}</div>", unsafe_allow_html=True)
    with c:
        if st.button("Next →", disabled=st.session_state.gallery_page >= page_count, use_container_width=True):
            st.session_state.gallery_page += 1
            st.rerun()
