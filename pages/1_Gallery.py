import math
import streamlit as st

from backend.drive import DriveGallery

user = st.session_state.get("gallery_user")
if not user or not user.get("active"):
    st.error("Please sign in again.")
    st.stop()

drive = DriveGallery()

st.markdown("""
<div class="glass-hero">
  <div class="eyebrow">BLUEGLASS · SHARED COLLECTION</div>
  <div class="hero-title">Your media, all together.</div>
  <div class="hero-copy">Search and explore every photo and video in the shared Google Drive collection.</div>
</div>
""", unsafe_allow_html=True)

if "shared_gallery_favourites" not in st.session_state:
    st.session_state.shared_gallery_favourites = set()
if "shared_gallery_page" not in st.session_state:
    st.session_state.shared_gallery_page = 1

# Fetch cached recursive media index. The first scan discovers nested folders;
# subsequent visits use the 30-minute cache unless manually refreshed.
try:
    with st.spinner("Loading your media library…"):
        media_all = drive.get_all_items()
except Exception as exc:
    st.error("Unable to load your shared Google Drive media.")
    st.exception(exc)
    st.stop()

media_count = len(media_all)
st.caption(f"{media_count:,} photos and videos")

# Global search and filters are the first controls; no album/folder browser.
c1, c2, c3, c4 = st.columns([2.5, 1.1, 1.2, 1.2])
with c1:
    search = st.text_input(
        "Search media",
        placeholder="Search by photo or video filename…",
        key="global_media_search",
        label_visibility="collapsed",
    )
with c2:
    kind = st.selectbox(
        "Media type", ["All media", "Photos", "Videos", "Favourites"],
        key="global_media_type", label_visibility="collapsed",
    )
with c3:
    sort_mode = st.selectbox(
        "Sort", ["Newest first", "Oldest first", "Name A–Z"],
        key="global_media_sort", label_visibility="collapsed",
    )
with c4:
    page_size = st.selectbox(
        "Per page", [24, 36, 48, 72],
        index=1, key="global_media_page_size", label_visibility="collapsed",
    )

media = list(media_all)
if search.strip():
    query = search.strip().casefold()
    media = [item for item in media if query in item.get("name", "").casefold()]
if kind == "Photos":
    media = [item for item in media if item.get("mimeType", "").startswith("image/")]
elif kind == "Videos":
    media = [item for item in media if item.get("mimeType", "").startswith("video/")]
elif kind == "Favourites":
    media = [item for item in media if item["id"] in st.session_state.shared_gallery_favourites]

if sort_mode == "Newest first":
    media.sort(key=lambda item: item.get("modifiedTime", ""), reverse=True)
elif sort_mode == "Oldest first":
    media.sort(key=lambda item: item.get("modifiedTime", ""))
else:
    media.sort(key=lambda item: item.get("name", "").casefold())

filter_signature = (search, kind, sort_mode, page_size)
if st.session_state.get("global_media_filter_signature") != filter_signature:
    st.session_state.global_media_filter_signature = filter_signature
    st.session_state.shared_gallery_page = 1

total_pages = max(1, math.ceil(len(media) / page_size))
st.session_state.shared_gallery_page = min(st.session_state.shared_gallery_page, total_pages)
page = st.session_state.shared_gallery_page
start = (page - 1) * page_size
visible = media[start:start + page_size]

st.markdown(f"**Showing {len(visible):,} of {len(media):,} matching items**")
st.divider()

@st.dialog("Media viewer", width="large")
def open_media(item):
    try:
        with st.spinner("Opening original media…"):
            content = drive.download_bytes(item)

        is_video = item.get("mimeType", "").startswith("video/")
        if is_video:
            st.video(content, format=item.get("mimeType"))
        else:
            zoom_key = f"media_zoom_{item['id']}"
            if zoom_key not in st.session_state:
                st.session_state[zoom_key] = 100
            z1, z2, z3 = st.columns([1, 4, 1])
            with z1:
                if st.button("−", key=f"zoom_out_{item['id']}", use_container_width=True):
                    st.session_state[zoom_key] = max(50, st.session_state[zoom_key] - 10)
            with z2:
                st.slider(
                    "Zoom",
                    min_value=50,
                    max_value=200,
                    step=10,
                    key=zoom_key,
                    label_visibility="collapsed",
                )
            with z3:
                if st.button("+", key=f"zoom_in_{item['id']}", use_container_width=True):
                    st.session_state[zoom_key] = min(200, st.session_state[zoom_key] + 10)

            display_width = int(850 * st.session_state[zoom_key] / 100)
            st.image(content, width=display_width)

        st.markdown(f"**{item.get('name', 'Untitled')}**")
        if item.get("modifiedTime"):
            st.caption("Modified " + item["modifiedTime"][:16].replace("T", " "))

        if user.get("can_download"):
            st.download_button(
                "Download original",
                data=content,
                file_name=item.get("name", "download"),
                mime=item.get("mimeType", "application/octet-stream"),
                use_container_width=True,
                key=f"download_{item['id']}",
            )
        else:
            st.caption("Original downloads are disabled for your account.")

        if st.button("Close viewer", key=f"close_{item['id']}", use_container_width=True):
            st.rerun()
    except Exception as exc:
        st.error(f"Could not open this media: {exc}")

if visible:
    with st.spinner("Loading previews…"):
        thumbnails = drive.fetch_thumbnails(visible, max_workers=12)

    columns_per_row = 6
    for row_start in range(0, len(visible), columns_per_row):
        row_items = visible[row_start:row_start + columns_per_row]
        row_thumbs = thumbnails[row_start:row_start + columns_per_row]
        cols = st.columns(columns_per_row, gap="small")
        for col, item, thumbnail in zip(cols, row_items, row_thumbs):
            with col:
                is_video = item.get("mimeType", "").startswith("video/")
                if thumbnail:
                    st.image(thumbnail, use_container_width=True)
                else:
                    label = "▶ VIDEO" if is_video else "PHOTO"
                    st.markdown(
                        f'<div class="media-placeholder">{label}</div>',
                        unsafe_allow_html=True,
                    )
                name = item.get("name", "Untitled")
                st.markdown(f'<div class="media-name" title="{name}">{name}</div>', unsafe_allow_html=True)

                action_cols = st.columns([1, 1], gap="small")
                with action_cols[0]:
                    favourite = item["id"] in st.session_state.shared_gallery_favourites
                    if st.button(
                        "★" if favourite else "☆",
                        key=f"favourite_{item['id']}",
                        help="Remove from favourites" if favourite else "Add to favourites",
                        use_container_width=True,
                    ):
                        if favourite:
                            st.session_state.shared_gallery_favourites.remove(item["id"])
                        else:
                            st.session_state.shared_gallery_favourites.add(item["id"])
                        st.rerun()
                with action_cols[1]:
                    action_label = "Play" if is_video else "Open"
                    if st.button(
                        action_label,
                        key=f"open_media_{item['id']}",
                        use_container_width=True,
                    ):
                        open_media(item)
else:
    st.info("No photos or videos match your search and filters.")

if total_pages > 1:
    st.divider()
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("← Previous", disabled=page <= 1, use_container_width=True):
            st.session_state.shared_gallery_page = page - 1
            st.rerun()
    with p2:
        st.markdown(
            f"<div class='page-indicator'>Page {page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with p3:
        if st.button("Next →", disabled=page >= total_pages, use_container_width=True):
            st.session_state.shared_gallery_page = page + 1
            st.rerun()

r1, r2 = st.columns([5, 1])
with r1:
    st.caption("Media is indexed recursively inside the configured Shared Gallery folder. Your personal Drive files outside that folder are not included.")
with r2:
    if st.button("↻ Refresh", use_container_width=True):
        drive.invalidate_index()
        st.rerun()
