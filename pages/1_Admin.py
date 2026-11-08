import streamlit as st

from backend.auth import require_google_user
from backend.drive import DriveGallery
from backend.ui import apply_theme, render_sidebar

st.set_page_config(page_title="Admin Studio", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

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

render_sidebar(user, active="admin", theme=theme)

st.markdown(
    "<div class='hero-panel'><div class='eyebrow'>YOUR PRIVATE DRIVE SPACE</div>"
    "<div class='hero-heading'>Admin Studio</div>"
    "<div class='hero-copy'>Upload, organise and manage the files in your personal gallery.</div></div>",
    unsafe_allow_html=True,
)
st.caption(f"Signed in as {user['email']} · Changes are limited to your gallery folder")

try:
    index = drive.get_index()
except Exception as exc:
    st.error("Unable to load your gallery folders.")
    st.exception(exc)
    st.stop()

folders = index["folders_by_id"]
media = [item for item in index["media"] if item.get("ownedByMe") is True]
children = index["children_by_parent"]
all_children = index["all_children_by_parent"]
folder_options = {root_id: "My Streamlit Gallery"}
for folder_id, folder in folders.items():
    if folder_id == root_id:
        continue
    parent_id = index["folder_parent"].get(folder_id)
    parent_name = folder_options.get(parent_id, "Album")
    label = f"{parent_name} / {folder['name']}"
    if label in folder_options.values():
        label = f"{label} · {folder_id[-5:]}"
    folder_options[folder_id] = label

folder_ids = list(folder_options.keys())
folder_labels = list(folder_options.values())
folder_label_to_id = {label: fid for fid, label in folder_options.items()}

section = st.segmented_control(
    "Admin section",
    ["Upload", "Manage media", "Albums", "Account"],
    default="Upload",
    key="admin_section",
    label_visibility="collapsed",
)

if section == "Upload":
    st.subheader("Add photos and videos")
    with st.container(border=True):
        destination_label = st.selectbox("Upload destination", folder_labels, key="upload_destination")
        destination_id = folder_label_to_id[destination_label]
        uploads = st.file_uploader(
            "Choose photos or videos",
            type=["jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff", "mp4", "mov", "m4v", "webm"],
            accept_multiple_files=True,
            help="Files are uploaded directly to the selected folder in the signed-in Google Drive account.",
        )
        st.caption("The app does not upload files to a shared Service Account. It uses your Google account.")
        if uploads and st.button("Upload to Google Drive", type="primary", use_container_width=True):
            progress = st.progress(0)
            status = st.empty()
            uploaded_count = 0
            for number, file in enumerate(uploads, start=1):
                try:
                    drive.upload_file(destination_id, file.name, file.getvalue(), file.type or "application/octet-stream", invalidate=False)
                    uploaded_count += 1
                    status.success(f"Uploaded {file.name}")
                except Exception as exc:
                    status.error(f"Failed to upload {file.name}: {exc}")
                progress.progress(number / len(uploads))
            drive.invalidate_index()
            st.success(f"Finished: {uploaded_count} of {len(uploads)} file(s) uploaded.")
            st.rerun()

if section == "Manage media":
    st.subheader("Manage your media")
    filter_col, type_col = st.columns([2, 1])
    with filter_col:
        file_search = st.text_input("Search your files", placeholder="Search by filename…", key="admin_search")
    with type_col:
        file_type = st.selectbox("Type", ["All media", "Photos", "Videos"], key="admin_type")

    filtered = media
    if file_search.strip():
        term = file_search.strip().casefold()
        filtered = [item for item in filtered if term in item.get("name", "").casefold()]
    if file_type == "Photos":
        filtered = [item for item in filtered if item.get("mimeType", "").startswith("image/")]
    elif file_type == "Videos":
        filtered = [item for item in filtered if item.get("mimeType", "").startswith("video/")]

    filtered.sort(key=lambda item: item.get("modifiedTime", ""), reverse=True)
    st.caption(f"{len(filtered):,} media file(s) in your gallery")

    if filtered:
        # Clear stale selections after a successful bulk operation, before rendering the widget again.
        if st.session_state.pop("clear_bulk_selection", False):
            st.session_state["bulk_select"] = []
        admin_page_size = 36
        if "admin_media_page" not in st.session_state:
            st.session_state.admin_media_page = 1
        admin_filter_key = (file_search, file_type)
        if st.session_state.get("admin_filter_key") != admin_filter_key:
            st.session_state.admin_filter_key = admin_filter_key
            st.session_state.admin_media_page = 1
            st.session_state.pop("bulk_select", None)
            st.session_state.pop("bulk_confirm", None)
        admin_pages = max(1, (len(filtered) + admin_page_size - 1) // admin_page_size)
        st.session_state.admin_media_page = min(st.session_state.admin_media_page, admin_pages)
        admin_start = (st.session_state.admin_media_page - 1) * admin_page_size
        display_items = filtered[admin_start:admin_start + admin_page_size]

        labels = {
            f"{item['name']} · {item.get('_gallery_parent_id', '')[-6:]} · {item['id'][-6:]}": item["id"]
            for item in display_items
        }
        selected_labels = st.multiselect(
            "Select multiple files",
            options=list(labels.keys()),
            key="bulk_select",
            help="Use this to move multiple selected files to Google Drive Trash.",
        )
        confirm_bulk = st.checkbox("I confirm moving the selected files to Trash", key="bulk_confirm")
        if st.button("Move selected to Trash", type="secondary",
                     disabled=not selected_labels or not confirm_bulk, use_container_width=True):
            done, errors = 0, []
            for label in selected_labels:
                try:
                    drive.trash_item(labels[label], invalidate=False)
                    done += 1
                except Exception as exc:
                    errors.append(f"{label}: {exc}")
            drive.invalidate_index()
            st.session_state["clear_bulk_selection"] = True
            st.success(f"Moved {done} file(s) to Trash.")
            for error in errors:
                st.warning(error)
            st.rerun()

        # Individual file actions, limited to the gallery index.
        admin_thumbnails = drive.fetch_thumbnails(display_items, max_workers=10)
        for item, preview in zip(display_items, admin_thumbnails):
            with st.container(border=True):
                left, mid, right = st.columns([1, 3, 2])
                with left:
                    if preview:
                        st.image(preview, use_container_width=True)
                    else:
                        st.markdown('<div class="media-placeholder">MEDIA</div>', unsafe_allow_html=True)
                with mid:
                    st.write(item["name"])
                    parent = folders.get(item.get("_gallery_parent_id"), {})
                    st.caption(f"{parent.get('name', 'Gallery root')} · {item.get('modifiedTime', '')[:10]}")
                    size = int(item.get("size", 0) or 0)
                    st.caption(f"{size / (1024 * 1024):.2f} MB")
                with right:
                    with st.popover("Manage", use_container_width=True):
                        new_name = st.text_input("Rename", value=item["name"], key=f"rename_{item['id']}")
                        if st.button("Save name", key=f"save_rename_{item['id']}", use_container_width=True):
                            try:
                                drive.rename_item(item["id"], new_name)
                                st.success("Renamed.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

                        destination_ids = [fid for fid in folder_ids if fid != item.get("_gallery_parent_id")]
                        if destination_ids:
                            destination_map = {folder_options[fid]: fid for fid in destination_ids}
                            move_to = st.selectbox("Move to album", list(destination_map.keys()), key=f"move_to_{item['id']}")
                            if st.button("Move file", key=f"move_file_{item['id']}", use_container_width=True):
                                try:
                                    drive.move_media(item["id"], destination_map[move_to])
                                    st.success("Moved.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(str(exc))

                        confirm = st.checkbox("Confirm move to Trash", key=f"trash_confirm_{item['id']}")
                        if st.button("Move to Trash", key=f"trash_{item['id']}",
                                     disabled=not confirm, use_container_width=True):
                            try:
                                drive.trash_item(item["id"])
                                st.success("Moved to Google Drive Trash.")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))
        if admin_pages > 1:
            pa, pb, pc = st.columns([1, 2, 1])
            with pa:
                if st.button("← Previous", disabled=st.session_state.admin_media_page <= 1, use_container_width=True):
                    st.session_state.admin_media_page -= 1
                    st.session_state["clear_bulk_selection"] = True
                    st.rerun()
            with pb:
                st.markdown(f"<div class='page-indicator'>Page {st.session_state.admin_media_page} of {admin_pages}</div>", unsafe_allow_html=True)
            with pc:
                if st.button("Next →", disabled=st.session_state.admin_media_page >= admin_pages, use_container_width=True):
                    st.session_state.admin_media_page += 1
                    st.session_state["clear_bulk_selection"] = True
                    st.rerun()
    else:
        st.info("No matching media in your gallery.")

if section == "Albums":
    st.subheader("Create and organise albums")
    with st.container(border=True):
        parent_label = st.selectbox("Create album inside", folder_labels, key="new_album_parent")
        new_album_name = st.text_input("Album name", placeholder="e.g. Travel 2026")
        if st.button("Create album", type="primary", use_container_width=True):
            try:
                drive.create_folder(new_album_name, folder_label_to_id[parent_label])
                st.success(f"Created album: {new_album_name}")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.markdown("#### Existing albums")
    non_root = [(fid, folder) for fid, folder in folders.items() if fid != root_id]
    for fid, folder in non_root:
        with st.container(border=True):
            a, b = st.columns([3, 2])
            with a:
                st.write("📁", folder["name"])
                st.caption(folder_options.get(fid, "Album"))
            with b:
                with st.popover("Album actions", use_container_width=True):
                    rename = st.text_input("Rename album", value=folder["name"], key=f"folder_rename_{fid}")
                    if st.button("Save album name", key=f"folder_save_{fid}"):
                        try:
                            drive.rename_item(fid, rename)
                            st.success("Album renamed.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
                    is_empty = not all_children.get(fid, [])
                    st.caption("Only empty albums can be moved to Trash from here.")
                    confirm_folder = st.checkbox("Confirm move to Trash", key=f"folder_confirm_{fid}")
                    if st.button("Move empty album to Trash", key=f"folder_trash_{fid}",
                                 disabled=(not is_empty or not confirm_folder)):
                        try:
                            drive.trash_item(fid)
                            st.success("Album moved to Trash.")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

if section == "Account":
    st.subheader("Connected Google account")
    st.write(user.get("name", "Google user"))
    st.write(user["email"])
    st.caption("Your app gallery root is owned by this Google account. Admin actions are checked against files inside this root.")
    st.code(root_id, language="text")
    st.link_button("Open my gallery folder in Google Drive", f"https://drive.google.com/drive/folders/{root_id}")
    st.warning("The OAuth permission requested is Google Drive access. The app restricts its management functions to your gallery root, but the granted OAuth token itself has broad Drive permissions.")
