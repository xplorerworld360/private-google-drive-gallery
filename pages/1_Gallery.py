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
  <div class="hero-title">Every moment, in one place.</div>
  <div class="hero-copy">Browse albums or explore every photo and video across your shared Google Drive collection.</div>
</div>
""", unsafe_allow_html=True)

for key, default in (
    ("shared_gallery_favourites", set()),
    ("shared_gallery_page", 1),
    ("shared_gallery_folder", root_id),
):
    if key not in st.session_state:
        st.session_state[key] = default

try:
    with st.spinner("Finding folders, photos and videos across your Drive…"):
        all_items = drive.get_all_items()
except Exception as exc:
    st.error("Unable to load your shared Google Drive gallery.")
    st.exception(exc)
    st.stop()

folders = [x for x in all_items if x.get("mimeType") == FOLDER_MIME]
media_all = [x for x in all_items if x.get("mimeType", "").startswith(("image/", "video/"))]
root_folders = drive.folder_items(root_id)
root_folders = sorted(
    [x for x in root_folders if x.get("mimeType") == FOLDER_MIME],
    key=lambda x: x.get("name", "").casefold()
)

# Folder browser is shown in the center of the page.
# st.markdown("### Your albums")
# if root_folders:
#     folder_cols = st.columns(4, gap="medium")
#     for i, folder in enumerate(root_folders):
#         with folder_cols[i % len(folder_cols)]:
#             with st.container(border=True):
#                 st.markdown("📁")
#                 st.markdown(f"**{folder.get('name', 'Untitled folder')}**")
#                 st.caption("Browse this folder")
#                 if st.button("Open folder →", key=f"open_folder_{folder['id']}", use_container_width=True):
#                     st.session_state.shared_gallery_folder = folder["id"]
#                     st.session_state.shared_gallery_current_folder = folder
#                     st.rerun()
# else:
#     st.caption("No subfolders found in the main gallery folder.")

# current_folder_id = st.session_state.shared_gallery_folder
# if current_folder_id != root_id:
#     current_folder = st.session_state.get("shared_gallery_current_folder", {"name": "Selected folder"})
#     back_col, name_col = st.columns([1, 5])
#     with back_col:
#         if st.button("← All albums", use_container_width=True):
#             st.session_state.shared_gallery_folder = root_id
#             st.session_state.pop("shared_gallery_current_folder", None)
#             st.rerun()
#     with name_col:
#         st.markdown(f"**Folder selected:** {current_folder.get('name', 'Selected folder')}")

# Global media explorer includes all nested folders and root-level media.
# st.markdown("---")
st.markdown("### All photos & videos")
st.caption(f"{len(media_all):,} media files found across {len(folders):,} folders.")

c1, c2, c3 = st.columns([2.4, 1, 1])
with c1:
    search = st.text_input("Search all media", placeholder="Search photos and videos by filename…", label_visibility="collapsed")
with c2:
    kind = st.selectbox("Media type", ["All media", "Photos", "Videos", "Favourites"], label_visibility="collapsed")
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

page_size = 48
pages = max(1, math.ceil(len(media) / page_size))
signature = (search, kind, sort_mode)
if st.session_state.get("shared_gallery_filter") != signature:
    st.session_state.shared_gallery_filter = signature
    st.session_state.shared_gallery_page = 1
st.session_state.shared_gallery_page = min(st.session_state.shared_gallery_page, pages)
start = (st.session_state.shared_gallery_page - 1) * page_size
visible = media[start:start + page_size]

st.caption(f"Showing {len(visible):,} of {len(media):,} matching files")
if visible:
    with st.spinner("Loading image previews…"):
        thumbs = drive.fetch_thumbnails(visible, max_workers=12)
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
                parent_name = item.get("_gallery_parent_id", "")
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
    st.info("No matching photos or videos found.")

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

# Full-size preview dialog with adjustable zoom for photos.
preview_item = st.session_state.get("shared_preview_item")
if preview_item and st.session_state.get("shared_preview_id") == preview_item.get("id"):
    @st.dialog("Gallery preview", width="large")
    def show_preview(item):
        try:
            content = drive.download_bytes(item)
            if item.get("mimeType", "").startswith("video/"):
                st.video(content, format=item.get("mimeType"))
            else:
                zoom = st.slider("Photo zoom", min_value=50, max_value=200, value=100, step=10, key=f"zoom_{item['id']}")
                display_width = min(1600, int(900 * zoom / 100))
                st.image(content, width=display_width)
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

if st.button("↻ Refresh Google Drive gallery"):
    drive.invalidate_index()
    st.rerun()
