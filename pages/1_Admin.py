import streamlit as st
from backend.auth import get_credentials,login,sidebar
from backend.drive import Drive

st.set_page_config(page_title="Admin Studio",page_icon="⚙️",layout="wide")
st.markdown("""<style>.block-container{max-width:1450px;padding-top:1.5rem}[data-testid="stAppViewContainer"]{background:linear-gradient(145deg,#10131b,#171d2a 55%,#11151e)}section[data-testid="stSidebar"]{background:#111722}div[data-testid="stImage"] img{border-radius:12px}</style>""",unsafe_allow_html=True)
creds=get_credentials()
if not creds: login(); st.stop()
sidebar(); drive=Drive(creds); albums=drive.albums()
st.title("⚙️ Admin Studio")
st.caption("Manage images and albums directly in your own Google Drive.")
tabs=st.tabs(["Upload images","Manage files","Manage albums"])
with tabs[0]:
    st.subheader("Upload to Drive")
    if albums:
        album=st.selectbox("Destination album",[a["name"] for a in albums])
        files=st.file_uploader("Drop image files or browse",type=["jpg","jpeg","png","gif","webp","bmp","tif","tiff"],accept_multiple_files=True)
        if files and st.button("Upload selected images",type="primary"):
            target=next(a for a in albums if a["name"]==album); progress=st.progress(0)
            for i,f in enumerate(files):
                drive.upload(target["id"],f.name,f.getvalue(),f.type or "application/octet-stream")
                progress.progress((i+1)/len(files))
            st.success(f"Uploaded {len(files)} image(s)."); st.rerun()
    else: st.info("Create an album first in Manage albums.")
with tabs[1]:
    st.subheader("Your Drive images")
    names=["All albums"]+[a["name"] for a in albums]
    selected=st.selectbox("Album filter",names)
    q=st.text_input("Search filenames")
    album_id=None if selected=="All albums" else next(a["id"] for a in albums if a["name"]==selected)
    items=drive.images(album_id,q.strip()); st.caption(f"{len(items)} image(s)")
    for item in items:
        with st.container(border=True):
            a,b,c=st.columns([1,3,2])
            with a:
                try: st.image(drive.download(item["id"]),use_container_width=True)
                except Exception: st.caption("Preview unavailable")
            with b:
                st.markdown(f"**{item['name']}**"); st.caption(item.get("modifiedTime","")[:16].replace("T"," "))
                if item.get("size"): st.caption(f"{int(item['size'])/1024:.1f} KB")
            with c:
                with st.popover("Manage file",use_container_width=True):
                    new=st.text_input("Rename",value=item["name"],key="rn"+item["id"])
                    if st.button("Save name",key="sv"+item["id"]):
                        drive.rename(item["id"],new.strip()); st.success("Renamed"); st.rerun()
                    st.download_button("Download original",drive.download(item["id"]),file_name=item["name"],key="ad"+item["id"],use_container_width=True)
                    confirm=st.checkbox("Confirm permanent deletion",key="cf"+item["id"])
                    if st.button("Delete from Drive",key="de"+item["id"],disabled=not confirm):
                        drive.delete(item["id"]); st.success("Deleted"); st.rerun()
with tabs[2]:
    st.subheader("Create and view albums")
    with st.form("newalbum"):
        name=st.text_input("Album name",placeholder="e.g. Travel 2026")
        ok=st.form_submit_button("Create album",type="primary")
        if ok:
            if name.strip(): drive.create_album(name.strip()); st.success("Album created"); st.rerun()
            else: st.error("Enter an album name.")
    st.divider()
    for a in albums:
        st.markdown(f"📁 **{a['name']}**")
