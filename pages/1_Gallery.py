import math
import streamlit as st

from backend.drive import DriveGallery

user = st.session_state.get("gallery_user")
if not user or not user.get("active"):
    st.error("Please sign in again.")
    st.stop()

drive = DriveGallery()
root_id = drive.root_id

st.markdown("""
<div class="glass-hero">
  <div class="eyebrow">BLUEGLASS · SHARED COLLECTION</div>
  <div class="hero-title">A little gallery of everything.</div>
  <div class="hero-copy">Explore albums and moments shared by the gallery owner.</div>
</div>
""", unsafe_allow_html=True)

try:
    with st.spinner("Preparing your gallery…"):
        index = drive.get_index()
except Exception as exc:
    st.error("Unable to read the shared Google Drive gallery.")
    st.exception(exc)
    st.stop()

folders_by_id = index["folders_by_id"]
children = index["children_by_parent"]
current_id = st.session_state.get("shared_gallery_folder", root_id)
if current_id not in folders_by_id:
    current_id = root_id
    st.session_state.shared_gallery_folder = root_id

current_folder = folders_by_id.get(current_id, {"name": "All Photos"})
if "shared_gallery_folder" not in st.session_state:
    st.session_state.shared_gallery_folder = root_id

# Sidebar album list is separate from image tiles.
with st.sidebar:
    st.markdown("### Browse")
    if st.button("◫  All Photos", key="shared_all_photos", use_container_width=True,
                 type="primary" if current_id == root_id else "secondary"):
        st.session_state.shared_gallery_folder = root_id
        st.rerun()
    root_folders = [
        item for item in children.get(root_id, [])
        if item.get("mimeType") == "application/vnd.google-apps.folder"
    ]
    for folder in sorted(root_folders, key=lambda item: item["name"].casefold()):
        if st.button("▧  " + folder["name"], key=f"album_nav_{folder['id']}",
                     use_container_width=True,
                     type="primary" if current_id == folder["id"] else "secondary"):
            st.session_state.shared_gallery_folder = folder["id"]
            st.rerun()

# Breadcrumb based on parent links.
crumbs = []
walk = current_id
while walk and walk != root_id:
    folder = folders_by_id.get(walk)
    if not folder:
        break
    crumbs.append(folder.get("name", "Album"))
    walk = index["folder_parent"].get(walk)
breadcrumb = "  /  ".join(["All Photos"] + list(reversed(crumbs)))

title = "All Photos" if current_id == root_id else current_folder.get("name", "Album")
st.subheader(title)
st.caption(breadcrumb)
refresh_col, info_col = st.columns([1, 5])
with refresh_col:
    if st.button("↻ Refresh library", use_container_width=True):
        drive.invalidate_index()
        st.rerun()
with info_col:
    st.caption("Photos are served from the owner's shared Drive library.")

# Interactive controls.
c1, c2, c3, c4 = st.columns([2.3, 1, 1, 1])
with c1:
    search = st.text_input("Search", placeholder="Search photos by filename…", label_visibility="collapsed")
with c2:
    sort_mode = st.selectbox("Sort", ["Newest first", "Oldest first", "Name A–Z"], label_visibility="collapsed")
with c3:
    density = st.selectbox("Layout", ["Comfortable", "Dense"], label_visibility="collapsed")
with c4:
    kind = st.selectbox("Media", ["All", "Photos", "Videos", "Favourites"], label_visibility="collapsed")

scope = st.radio("Search in", ["This album", "Entire gallery"], horizontal=True, label_visibility="collapsed")
target_folder = root_id if scope == "Entire gallery" else current_id
media = drive.media_in_folder(target_folder, recursive=True)

if search.strip():
    q = search.strip().casefold()
    media = [item for item in media if q in item.get("name", "").casefold()]

if kind == "Photos":
    media = [item for item in media if item.get("mimeType", "").startswith("image/")]
elif kind == "Videos":
    media = [item for item in media if item.get("mimeType", "").startswith("video/")]
elif kind == "Favourites":
    favs = st.session_state.get("shared_gallery_favourites", set())
    media = [item for item in media if item["id"] in favs]

if sort_mode == "Newest first":
    media.sort(key=lambda item: item.get("modifiedTime", ""), reverse=True)
elif sort_mode == "Oldest first":
    media.sort(key=lambda item: item.get("modifiedTime", ""))
else:
    media.sort(key=lambda item: item.get("name", "").casefold())

if "shared_gallery_favourites" not in st.session_state:
    st.session_state.shared_gallery_favourites = set()

direct_folders = [
    item for item in children.get(current_id, [])
    if item.get("mimeType") == "application/vnd.google-apps.folder"
]
if direct_folders and scope == "This album" and not search.strip():
    st.markdown("#### Albums")
    folder_cols = st.columns(5 if density == "Dense" else 4, gap="small")
    for i, folder in enumerate(sorted(direct_folders, key=lambda item: item["name"].casefold())):
        with folder_cols[i % len(folder_cols)]:
            with st.container(border=True):
                st.markdown("📁 **" + folder["name"] + "**")
                if st.button("Open album →", key=f"open_shared_{folder['id']}", use_container_width=True):
                    st.session_state.shared_gallery_folder = folder["id"]
                    st.rerun()

st.markdown("#### Collection")
st.caption(f"{len(media):,} item(s)")

page_size = 72
pages = max(1, math.ceil(len(media) / page_size))
if "shared_gallery_page" not in st.session_state:
    st.session_state.shared_gallery_page = 1
filter_signature = (target_folder, current_id, search, kind, sort_mode, density)
if st.session_state.get("shared_gallery_filter") != filter_signature:
    st.session_state.shared_gallery_filter = filter_signature
    st.session_state.shared_gallery_page = 1
st.session_state.shared_gallery_page = min(st.session_state.shared_gallery_page, pages)
start = (st.session_state.shared_gallery_page - 1) * page_size
visible = media[start:start + page_size]

if visible:
    thumbs = drive.fetch_thumbnails(visible, max_workers=12)
    columns = 7 if density == "Dense" else 5
    for row_start in range(0, len(visible), columns):
        cols = st.columns(columns, gap="small")
        row = visible[row_start:row_start + columns]
        row_thumbs = thumbs[row_start:row_start + columns]
        for col, item, thumb in zip(cols, row, row_thumbs):
            with col:
                if thumb:
                    st.image(thumb, use_container_width=True)
                else:
                    st.markdown('<div class="media-placeholder">MEDIA</div>', unsafe_allow_html=True)
                st.caption(item["name"])
                fcol, vcol = st.columns([1, 1])
                fav = item["id"] in st.session_state.shared_gallery_favourites
                with fcol:
                    if st.button("★" if fav else "☆", key=f"fav_{item['id']}", use_container_width=True):
                        if fav:
                            st.session_state.shared_gallery_favourites.remove(item["id"])
                        else:
                            st.session_state.shared_gallery_favourites.add(item["id"])
                        st.rerun()
                with vcol:
                    if st.button("View", key=f"view_{item['id']}", use_container_width=True):
                        st.session_state.shared_preview_id = item["id"]
                        st.rerun()
else:
    st.info("No media matches this selection.")

# Full-size media only downloads after the visitor opens it.
if st.session_state.get("shared_preview_id"):
    preview_item = next((item for item in media if item["id"] == st.session_state.shared_preview_id), None)
    if preview_item is None:
        st.session_state.pop("shared_preview_id", None)
    else:
        @st.dialog("Gallery preview", width="large")
        def show_preview(item):
            try:
                content = drive.download_bytes(item)
                if item.get("mimeType", "").startswith("video/"):
                    st.video(content, format=item.get("mimeType"))
                else:
                    st.image(content, use_container_width=True)
                st.write(item["name"])
                st.caption(item.get("modifiedTime", "")[:16].replace("T", " "))
                if user.get("can_download"):
                    st.download_button("Download original", content, file_name=item["name"],
                                       mime=item.get("mimeType", "application/octet-stream"),
                                       use_container_width=True)
                else:
                    st.caption("Downloads are not enabled for your account.")
                idx = next((i for i, x in enumerate(media) if x["id"] == item["id"]), 0)
                pcol, ncol, closecol = st.columns(3)
                with pcol:
                    if st.button("← Previous", disabled=len(media) < 2, use_container_width=True):
                        st.session_state.shared_preview_id = media[(idx - 1) % len(media)]["id"]
                        st.rerun()
                with ncol:
                    if st.button("Next →", disabled=len(media) < 2, use_container_width=True):
                        st.session_state.shared_preview_id = media[(idx + 1) % len(media)]["id"]
                        st.rerun()
                with closecol:
                    if st.button("Close", use_container_width=True):
                        st.session_state.pop("shared_preview_id", None)
                        st.rerun()
            except Exception as exc:
                st.error(f"Unable to open media: {exc}")
        show_preview(preview_item)

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
