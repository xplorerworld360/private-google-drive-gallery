import streamlit as st
from backend.auth import require_login
from backend.google_drive import DriveGallery, DriveError

st.set_page_config(page_title="Private Drive Gallery", page_icon="🖼️", layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 1.8rem; max-width: 1500px;}
[data-testid="stImage"] img {border-radius: 10px;}
.gallery-caption {font-size: .88rem; opacity: .8; overflow-wrap: anywhere;}
</style>
""", unsafe_allow_html=True)

require_login()
st.title("🖼️ My Private Gallery")
st.caption("Your albums and images are loaded directly from your Google Drive.")

@st.cache_resource
def get_gallery():
    return DriveGallery()

try:
    drive = get_gallery()
    albums = drive.list_albums()
except Exception as exc:
    st.error(f"Could not connect to Google Drive: {exc}")
    st.info("Check the setup instructions and your Streamlit secrets.")
    st.stop()

if not albums:
    st.warning("No album folders found in the configured Google Drive folder.")
    st.stop()

tab_gallery, tab_admin = st.tabs(["Gallery", "Admin"])

with tab_gallery:
    names = ["All albums"] + [a["name"] for a in albums]
    selected_album = st.selectbox("Album", names)
    query = st.text_input("Search images", placeholder="Search by filename…")
    album_map = {a["name"]: a for a in albums}
    selected = None if selected_album == "All albums" else album_map[selected_album]

    with st.spinner("Loading images…"):
        images = drive.list_images(selected["id"] if selected else None, query=query.strip())

    st.caption(f"{len(images)} image(s)")
    if not images:
        st.info("No images match your selection.")
    else:
        cols = st.columns(4)
        for i, item in enumerate(images):
            with cols[i % 4]:
                try:
                    data = drive.download_bytes(item["id"])
                    st.image(data, use_container_width=True)
                    st.markdown(f'<div class="gallery-caption">{item["name"]}</div>', unsafe_allow_html=True)
                    st.download_button(
                        "⬇️ Download",
                        data=data,
                        file_name=item["name"],
                        mime=item.get("mimeType", "application/octet-stream"),
                        key=f"download_{item['id']}",
                        use_container_width=True,
                    )
                except Exception as exc:
                    st.warning(f"Unable to load {item['name']}: {exc}")

with tab_admin:
    st.subheader("Gallery administration")
    st.markdown("Upload images into an album or create a new album folder.")
    album_names = [a["name"] for a in albums]
    upload_album_name = st.selectbox("Upload destination", album_names, key="upload_album")
    uploaded = st.file_uploader(
        "Choose image files",
        type=["jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff"],
        accept_multiple_files=True,
    )
    if st.button("Upload selected images", type="primary", disabled=not uploaded):
        target = next(a for a in albums if a["name"] == upload_album_name)
        progress = st.progress(0)
        status = st.empty()
        for index, file in enumerate(uploaded):
            try:
                drive.upload_file(target["id"], file.name, file.getvalue(), file.type or "application/octet-stream")
                status.success(f"Uploaded {file.name}")
            except Exception as exc:
                status.error(f"Failed to upload {file.name}: {exc}")
            progress.progress((index + 1) / len(uploaded))
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Create an album")
    new_album = st.text_input("New album name")
    if st.button("Create album", disabled=not new_album.strip()):
        try:
            drive.create_album(new_album.strip())
            st.success(f"Created album: {new_album}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Delete an image")
    delete_album = st.selectbox("Album to manage", album_names, key="delete_album")
    target = next(a for a in albums if a["name"] == delete_album)
    delete_images = drive.list_images(target["id"])
    if delete_images:
        choice = st.selectbox("Image", delete_images, format_func=lambda x: x["name"])
        confirm = st.checkbox("I understand this permanently deletes the file from Google Drive.")
        if st.button("Delete selected image", type="secondary", disabled=not confirm):
            try:
                drive.delete_file(choice["id"])
                st.success("Image deleted from Google Drive.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    else:
        st.caption("This album has no images.")
