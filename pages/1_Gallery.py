import math
import streamlit as st

from backend.drive import DriveGallery, FOLDER_MIME

user = st.session_state.get("gallery_user")
if not user or not user.get("active"):
    st.error("Please sign in again.")
    st.stop()

drive = DriveGallery()
root_id = drive.root_id

st.markdown("""
<div class="glass-hero">
  <div class="eyebrow">BLUEGLASS · SHARED COLLECTION</div>
  <div class="hero-title">Browse your albums.</div>
  <div class="hero-copy">Choose a folder to explore its photos and videos. Media loads only when you open an album.</div>
</div>
""", unsafe_allow_html=True)

if "shared_gallery_folder" not in st.session_state:
    st.session_state.shared_gallery_folder = root_id
if "shared_gallery_favourites" not in st.session_state:
    st.session_state.shared_gallery_favourites = set()
if "shared_gallery_page" not in st.session_state:
    st.session_state.shared_gallery_page = 1

current_id = st.session_state.shared_gallery_folder
if current_id == root_id:
    current_folder = {"name": "Albums"}
else:
    current_folder = st.session_state.get("shared_gallery_current_folder", {"name": "Album"})

try:
    with st.spinner("Loading folders…" if current_id == root_id else "Loading album…"):
        items = drive.folder_items(current_id)
except Exception as exc:
    st.error("Unable to load this Google Drive folder.")
    st.exception(exc)
    st.stop()

folders = sorted(
    [x for x in items if x.get("mimeType") == FOLDER_MIME],
    key=lambda x: x.get("name", "").casefold()
)
media_all = [x for x in items if x.get("mimeType", "").startswith(("image/", "video/"))]
for item in media_all:
    item["_gallery_parent_id"] = current_id

# Build breadcrumbs from the navigation history maintained by folder clicks.
if "shared_gallery_breadcrumbs" not in st.session_state:
    st.session_state.shared_gallery_breadcrumbs = []
crumbs = st.session_state.shared_gallery_breadcrumbs
st.subheader("Albums" if current_id == root_id else current_folder.get("name", "Album"))

nav_cols = st.columns([1, 5, 1])
with nav_cols[0]:
    if current_id != root_id and st.button("← All albums", use_container_width=True):
        st.session_state.shared_gallery_folder = root_id
        st.session_state.shared_gallery_breadcrumbs = []
        st.session_state.pop("shared_gallery_current_folder", None)
        st.session_state.shared_gallery_page = 1
        st.rerun()
with nav_cols[1]:
    if current_id != root_id:
        labels = ["Albums"] + [x.get("name", "Album") for x in crumbs]
        st.caption("  /  ".join(labels))
    else:
        st.caption("Select an album below. The app does not scan every nested folder at startup.")
with nav_cols[2]:
    if st.button("↻ Refresh", use_container_width=True):
        drive.invalidate_index()
        st.rerun()

# Folder cards appear in the main content area, not the sidebar.
if folders:
    st.markdown("### Folders")
    folder_cols = st.columns(4, gap="medium")
    for i, folder in enumerate(folders):
        with folder_cols[i % len(folder_cols)]:
            with st.container(border=True):
                st.markdown("📁")
                st.markdown(f"**{folder.get('name', 'Untitled folder')}**")
                st.caption("Open to view contents")
                if st.button("Open folder →", key=f"open_folder_{folder['id']}", use_container_width=True):
                    st.session_state.shared_gallery_breadcrumbs = crumbs + ([current_folder] if current_id != root_id else [])
                    st.session_state.shared_gallery_folder = folder["id"]
                    st.session_state.shared_gallery_current_folder = folder
                    st.session_state.shared_gallery_page = 1
                    st.rerun()

# Root view is folder-first. Only show loose files when explicitly expanded.
if current_id == root_id:
    if media_all:
        with st.expander(f"Unsorted items in root ({len(media_all)})", expanded=False):
            st.caption("These are files stored directly in the main gallery folder, outside any album.")
            show_media = True
    else:
        show_media = False
else:
    show_media = True

if show_media:
    st.markdown("### Photos & videos")
    c1, c2, c3 = st.columns([2.2, 1, 1])
    with c1:
        search = st.text_input("Search this folder", placeholder="Search filenames…", label_visibility="collapsed")
    with c2:
        kind = st.selectbox("Media type", ["All", "Photos", "Videos", "Favourites"], label_visibility="collapsed")
    with c3:
        sort_mode = st.selectbox("Sort", ["Newest first", "Oldest first", "Name A–Z"], label_visibility="collapsed")

    media = list(media_all)
    if search.strip():
        q = search.strip().casefold()
        media = [x for x in media if q in x.get("name", "").casefold()]
    if kind == "Photos":
        media = [x for x in media if x.get("mimeType", "").startswith("image/")]
    elif kind == "Videos":
        media = [x for x in media if x.get("mimeType", "").startswith("video/")]
    elif kind == "Favourites":
        media = [x for x in media if x["id"] in st.session_state.shared_gallery_favourites]

    if sort_mode == "Newest first":
        media.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
    elif sort_mode == "Oldest first":
        media.sort(key=lambda x: x.get("modifiedTime", ""))
    else:
        media.sort(key=lambda x: x.get("name", "").casefold())

    st.caption(f"{len(media):,} item(s) in this folder")
    page_size = 48
    pages = max(1, math.ceil(len(media) / page_size))
    signature = (current_id, search, kind, sort_mode)
    if st.session_state.get("shared_gallery_filter") != signature:
        st.session_state.shared_gallery_filter = signature
        st.session_state.shared_gallery_page = 1
    st.session_state.shared_gallery_page = min(st.session_state.shared_gallery_page, pages)
    start = (st.session_state.shared_gallery_page - 1) * page_size
    visible = media[start:start + page_size]

    if visible:
        with st.spinner("Loading previews…"):
            thumbs = drive.fetch_thumbnails(visible, max_workers=8)
        columns = 6
        for row_start in range(0, len(visible), columns):
            cols = st.columns(columns, gap="small")
            for col, item, thumb in zip(cols, visible[row_start:row_start+columns], thumbs[row_start:row_start+columns]):
                with col:
                    if thumb:
                        st.image(thumb, use_container_width=True)
                    else:
                        st.markdown('<div class="media-placeholder">PHOTO / VIDEO</div>', unsafe_allow_html=True)
                    st.caption(item.get("name", "Untitled"))
                    a, b = st.columns(2)
                    fav = item["id"] in st.session_state.shared_gallery_favourites
                    with a:
                        if st.button("★" if fav else "☆", key=f"fav_{item['id']}", use_container_width=True):
                            if fav:
                                st.session_state.shared_gallery_favourites.remove(item["id"])
                            else:
                                st.session_state.shared_gallery_favourites.add(item["id"])
                            st.rerun()
                    with b:
                        if st.button("View", key=f"view_{item['id']}", use_container_width=True):
                            st.session_state.shared_preview_id = item["id"]
                            st.session_state.shared_preview_item = item
                            st.rerun()
    else:
        st.info("No photos or videos in this folder.")

    if pages > 1:
        p1, p2, p3 = st.columns([1, 2, 1])
        with p1:
            if st.button("← Previous", disabled=st.session_state.shared_gallery_page <= 1, use_container_width=True):
                st.session_state.shared_gallery_page -= 1
                st.rerun()
        with p2:
            st.markdown(f"<div class='page-indicator'>Page {st.session_state.shared_gallery_page} of {pages}</div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next →", disabled=st.session_state.shared_gallery_page >= pages, use_container_width=True):
                st.session_state.shared_gallery_page += 1
                st.rerun()
elif not folders:
    st.info("This folder is empty. Add subfolders or media to your shared Google Drive folder.")

# Preview is fetched only after the visitor chooses View.
preview_item = st.session_state.get("shared_preview_item")
if preview_item and st.session_state.get("shared_preview_id") == preview_item.get("id"):
    @st.dialog("Gallery preview", width="large")
    def show_preview(item):
        try:
            content = drive.download_bytes(item)
            if item.get("mimeType", "").startswith("video/"):
                st.video(content, format=item.get("mimeType"))
            else:
                st.image(content, use_container_width=True)
            st.write(item.get("name", ""))
            st.caption(item.get("modifiedTime", "")[:16].replace("T", " "))
            if user.get("can_download"):
                st.download_button("Download original", content, file_name=item.get("name", "download"),
                                   mime=item.get("mimeType", "application/octet-stream"), use_container_width=True)
            else:
                st.caption("Downloads are not enabled for your account.")
            if st.button("Close preview", use_container_width=True):
                st.session_state.pop("shared_preview_id", None)
                st.session_state.pop("shared_preview_item", None)
                st.rerun()
        except Exception as exc:
            st.error(f"Unable to open media: {exc}")
    show_preview(preview_item)
