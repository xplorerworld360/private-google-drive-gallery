import math
import streamlit as st

from backend.auth import require_google_user
from backend.drive import DriveGallery
from backend.ui import apply_theme, render_sidebar

st.set_page_config(page_title="Photos", page_icon="📷", layout="wide", initial_sidebar_state="expanded")

theme = apply_theme()
auth = require_google_user()
if not auth:
    st.stop()
credentials, user = auth

try:
    drive = DriveGallery(credentials, user)
    root_id = drive.root_id
except Exception as exc:
    st.error("Could not connect to this Google Drive account.")
    st.exception(exc)
    st.stop()

render_sidebar(user, active="gallery", theme=theme)

st.markdown(
    f"<div class='hero-panel'><div class='eyebrow'>YOUR PERSONAL LIBRARY</div>"
    f"<div class='hero-heading'>Photos</div>"
    f"<div class='hero-copy'>A calm, private space for your photos and videos.</div></div>",
    unsafe_allow_html=True,
)
st.caption(f"Connected as {user['email']}")

try:
    with st.spinner("Preparing your gallery…" if not st.session_state.get("gallery_index_loaded") else ""):
        index = drive.get_index()
        st.session_state["gallery_index_loaded"] = True
except Exception as exc:
    st.error("Could not load your Google Drive gallery.")
    st.exception(exc)
    st.stop()

folders_by_id = index["folders_by_id"]
media = [item for item in index["media"] if item.get("ownedByMe") is True]
children_by_parent = index["children_by_parent"]

# Root / album navigation.
if "selected_folder_id" not in st.session_state:
    st.session_state.selected_folder_id = root_id
if st.session_state.selected_folder_id not in folders_by_id and st.session_state.selected_folder_id != root_id:
    st.session_state.selected_folder_id = root_id

current_folder_id = st.session_state.selected_folder_id
current_folder = folders_by_id.get(current_folder_id, {"name": "All Photos"})
current_title = "All Photos" if current_folder_id == root_id else current_folder.get("name", "Album")
breadcrumb_names = []
walk_id = current_folder_id
while walk_id and walk_id != root_id:
    folder = folders_by_id.get(walk_id)
    if not folder:
        break
    breadcrumb_names.append(folder.get("name", "Album"))
    walk_id = index["folder_parent"].get(walk_id)
breadcrumb_text = " / ".join(["All Photos"] + list(reversed(breadcrumb_names)))

with st.sidebar:
    st.markdown("### Albums")
    if st.button("▦  All Photos", key="nav_all_photos", use_container_width=True,
                 type="primary" if current_folder_id == root_id else "secondary"):
        st.session_state.selected_folder_id = root_id
        st.rerun()
    root_folders = [
        item for item in children_by_parent.get(root_id, [])
        if item.get("mimeType") == "application/vnd.google-apps.folder"
    ]
    for folder in sorted(root_folders, key=lambda x: x["name"].casefold()):
        if st.button("▣  " + folder["name"], key=f"nav_folder_{folder['id']}",
                     use_container_width=True,
                     type="primary" if current_folder_id == folder["id"] else "secondary"):
            st.session_state.selected_folder_id = folder["id"]
            st.rerun()

st.subheader(current_title)
if current_folder_id != root_id:
    st.caption(breadcrumb_text)
    if st.button("← Back to All Photos"):
        st.session_state.selected_folder_id = root_id
        st.rerun()

# Toolbar.
c1, c2, c3, c4 = st.columns([2.4, 1.0, 1.0, 1.0])
with c1:
    query = st.text_input("Search", placeholder="⌕  Search photos and videos…", label_visibility="collapsed")
with c2:
    sort_mode = st.selectbox("Sort", ["Newest first", "Oldest first", "Name A–Z", "Name Z–A"], label_visibility="collapsed")
with c3:
    density = st.selectbox("Grid", ["Comfortable", "Dense"], label_visibility="collapsed")
with c4:
    media_type = st.selectbox("Media", ["All", "Photos", "Videos", "Favourites"], label_visibility="collapsed")

search_scope = st.radio("Search scope", ["Current album", "Entire library"], horizontal=True, label_visibility="collapsed")
target_folder_id = root_id if search_scope == "Entire library" else current_folder_id

items = drive.media_in_folder(target_folder_id, recursive=True)
if query.strip():
    q = query.strip().casefold()
    items = [x for x in items if q in x.get("name", "").casefold()]

if media_type == "Photos":
    items = [x for x in items if x.get("mimeType", "").startswith("image/")]
elif media_type == "Videos":
    items = [x for x in items if x.get("mimeType", "").startswith("video/")]
elif media_type == "Favourites":
    favs = st.session_state.get("gallery_favourites", set())
    items = [x for x in items if x["id"] in favs]

if sort_mode == "Newest first":
    items.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
elif sort_mode == "Oldest first":
    items.sort(key=lambda x: x.get("modifiedTime", ""))
elif sort_mode == "Name A–Z":
    items.sort(key=lambda x: x.get("name", "").casefold())
else:
    items.sort(key=lambda x: x.get("name", "").casefold(), reverse=True)

if "gallery_favourites" not in st.session_state:
    st.session_state.gallery_favourites = set()

# Summary strip.
total_photo = sum(1 for x in items if x.get("mimeType", "").startswith("image/"))
total_video = len(items) - total_photo
m1, m2, m3 = st.columns(3)
m1.metric("Items", f"{len(items):,}")
m2.metric("Photos", f"{total_photo:,}")
m3.metric("Videos", f"{total_video:,}")

# Child folders appear as album tiles, never mixed into the media grid.
direct_folders = [
    item for item in children_by_parent.get(current_folder_id, [])
    if item.get("mimeType") == "application/vnd.google-apps.folder"
]
if direct_folders:
    st.markdown("#### Albums and folders")
    folder_cols = st.columns(5 if density == "Dense" else 4, gap="small")
    for i, folder in enumerate(sorted(direct_folders, key=lambda x: x["name"].casefold())):
        with folder_cols[i % len(folder_cols)]:
            with st.container(border=True):
                st.write("📁", folder["name"])
                desc_count = len(drive.media_in_folder(folder["id"], recursive=True))
                st.caption(f"{desc_count:,} media items")
                if st.button("Open album →", key=f"open_album_{folder['id']}", use_container_width=True):
                    st.session_state.selected_folder_id = folder["id"]
                    st.rerun()

st.markdown("#### Your collection")
st.caption(f"{len(items):,} matching items · sorted by {sort_mode.lower()}")

# Paginate metadata before fetching thumbnails.
PAGE_SIZE = 72
page_count = max(1, math.ceil(len(items) / PAGE_SIZE))
if "gallery_page" not in st.session_state:
    st.session_state.gallery_page = 1
filter_key = (target_folder_id, current_folder_id, query, media_type, sort_mode, density)
if st.session_state.get("gallery_filter_key") != filter_key:
    st.session_state.gallery_filter_key = filter_key
    st.session_state.gallery_page = 1
st.session_state.gallery_page = min(st.session_state.gallery_page, page_count)
start = (st.session_state.gallery_page - 1) * PAGE_SIZE
visible = items[start:start + PAGE_SIZE]

if not visible:
    st.info("No matching photos or videos. Upload media in Admin Studio or change your filters.")
else:
    thumbs = drive.fetch_thumbnails(visible, max_workers=12)
    cols_per_row = 7 if density == "Dense" else 5
    for row_start in range(0, len(visible), cols_per_row):
        row_items = visible[row_start:row_start + cols_per_row]
        row_thumbs = thumbs[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row, gap="small")
        for col, item, thumb in zip(cols, row_items, row_thumbs):
            with col:
                is_video = item.get("mimeType", "").startswith("video/")
                if thumb:
                    st.image(thumb, use_container_width=True)
                else:
                    st.markdown(
                        '<div class="media-placeholder">▶ VIDEO</div>' if is_video
                        else '<div class="media-placeholder">PHOTO</div>',
                        unsafe_allow_html=True,
                    )
                st.caption(item["name"])
                meta_left, meta_right = st.columns([1, 1])
                with meta_left:
                    fav = item["id"] in st.session_state.gallery_favourites
                    if st.button("★" if fav else "☆", key=f"favorite_{item['id']}", help="Toggle favourite", use_container_width=True):
                        if fav:
                            st.session_state.gallery_favourites.remove(item["id"])
                        else:
                            st.session_state.gallery_favourites.add(item["id"])
                        st.rerun()
                with meta_right:
                    if st.button("View", key=f"view_{item['id']}", use_container_width=True):
                        st.session_state.preview_item_id = item["id"]
                        st.rerun()

if page_count > 1:
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("← Previous", disabled=st.session_state.gallery_page <= 1, use_container_width=True):
            st.session_state.gallery_page -= 1
            st.rerun()
    with p2:
        st.markdown(f"<div class='page-indicator'>Page {st.session_state.gallery_page} of {page_count}</div>", unsafe_allow_html=True)
    with p3:
        if st.button("Next →", disabled=st.session_state.gallery_page >= page_count, use_container_width=True):
            st.session_state.gallery_page += 1
            st.rerun()

# Full-size bytes are fetched only after the user clicks View.
if st.session_state.get("preview_item_id"):
    preview_id = st.session_state.preview_item_id
    item = next((x for x in items if x["id"] == preview_id), None)
    if item:
        @st.dialog("Preview", width="large")
        def preview_dialog(selected):
            try:
                original = drive.download_bytes(selected["id"])
                if selected.get("mimeType", "").startswith("video/"):
                    st.video(original, format=selected.get("mimeType"))
                else:
                    st.image(original, use_container_width=True)
                st.markdown(f"**{selected['name']}**")
                st.caption(selected.get("modifiedTime", "")[:16].replace("T", " "))
                left, center, right = st.columns([1, 1, 1])
                with left:
                    current_index = next((i for i, x in enumerate(items) if x["id"] == selected["id"]), 0)
                    if st.button("← Previous", use_container_width=True, disabled=len(items) < 2):
                        st.session_state.preview_item_id = items[(current_index - 1) % len(items)]["id"]
                        st.rerun()
                with center:
                    st.download_button("Download original", original, file_name=selected["name"],
                                       mime=selected.get("mimeType", "application/octet-stream"),
                                       use_container_width=True)
                with right:
                    if st.button("Next →", use_container_width=True, disabled=len(items) < 2):
                        st.session_state.preview_item_id = items[(current_index + 1) % len(items)]["id"]
                        st.rerun()
            except Exception as exc:
                st.error(f"Could not open this media: {exc}")
            if st.button("Close preview", use_container_width=True):
                st.session_state.pop("preview_item_id", None)
                st.rerun()
        preview_dialog(item)
    else:
        st.session_state.pop("preview_item_id", None)
