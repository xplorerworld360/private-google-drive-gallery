import base64
import json
import math
import streamlit as st
import streamlit.components.v1 as components

from backend.auth import require_login
from backend.drive import DriveGallery

st.set_page_config(page_title="Photos", page_icon="📷", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700;750;800&display=swap');
:root{color-scheme:light}
html,body,[class*="css"]{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
[data-testid="stAppViewContainer"]{background:#f5f5f7;color:#1d1d1f}
[data-testid="stHeader"]{background:rgba(245,245,247,.88);backdrop-filter:blur(18px)}
.block-container{max-width:1700px;padding:1.25rem 2rem 3rem}
section[data-testid="stSidebar"]{background:#fbfbfd;border-right:1px solid #e7e7eb}
section[data-testid="stSidebar"] *{color:#27272a}
h1,h2,h3{color:#1d1d1f;font-family:Inter,sans-serif;letter-spacing:-.04em}
h1{font-weight:750}
h2{font-weight:700}
div[data-testid="stTextInput"] input,div[data-testid="stSelectbox"] div[role="combobox"]{border-radius:12px;background:#fff;border-color:#e2e2e7}
div.stButton>button{border-radius:11px;border:1px solid #e2e2e7;background:#fff;color:#222}
div.stButton>button:hover{border-color:#aaa;background:#f7f7f9;color:#111}
div[data-testid="stAlert"]{border-radius:14px}
.topline{color:#86868b;font-size:.78rem;font-weight:650;letter-spacing:.08em;text-transform:uppercase}
.subtitle{color:#6e6e73;font-size:.94rem}
.section-title{font-size:1.1rem;font-weight:700;letter-spacing:-.025em;color:#1d1d1f}
div[data-testid="stHorizontalBlock"]{gap:.75rem}
</style>
""", unsafe_allow_html=True)

require_login()

@st.cache_resource
def get_drive():
    return DriveGallery()

try:
    drive = get_drive()
    root_id = drive.root_id
except Exception as exc:
    st.error("Google Drive connection failed.")
    st.code(str(exc))
    st.info("Check the service-account details in Streamlit Secrets, share the root folder with the service-account email as Viewer, and ensure Google Drive API is enabled.")
    if st.button("Try again"):
        st.rerun()
    st.stop()

# Keep navigation in session state. Root means all photos recursively, not only direct children.
if "current_folder_id" not in st.session_state:
    st.session_state.current_folder_id = root_id
if "current_folder_name" not in st.session_state:
    st.session_state.current_folder_name = "All Photos"
if "folder_breadcrumb" not in st.session_state:
    st.session_state.folder_breadcrumb = []

current_id = st.session_state.current_folder_id
current_name = st.session_state.current_folder_name
is_root = current_id == root_id

with st.sidebar:
    st.markdown("## Photos")
    st.caption("Your private Google Drive library")
    st.divider()
    if st.button("▦  All Photos", use_container_width=True, type="primary" if is_root else "secondary"):
        st.session_state.current_folder_id = root_id
        st.session_state.current_folder_name = "All Photos"
        st.session_state.folder_breadcrumb = []
        st.rerun()
    st.markdown("**Albums & folders**")
    try:
        root_folders = drive.list_folders(root_id)
        for folder in root_folders:
            selected = current_id == folder["id"]
            if st.button(("▣  " if selected else "▢  ") + folder["name"], key=f"side_{folder['id']}", use_container_width=True):
                st.session_state.current_folder_id = folder["id"]
                st.session_state.current_folder_name = folder["name"]
                st.session_state.folder_breadcrumb = [{"id":folder["id"],"name":folder["name"]}]
                st.rerun()
    except Exception as exc:
        st.caption(f"Could not list folders: {exc}")
    st.divider()
    if st.button("↻  Refresh library", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.link_button("Open Google Drive ↗", "https://drive.google.com/drive/my-drive", use_container_width=True)
    st.divider()
    st.caption("Manage folders and files directly in Google Drive. This app only reads your collection.")

# Header and compact controls
st.markdown('<div class="topline">YOUR LIBRARY</div>', unsafe_allow_html=True)
if is_root:
    st.title("All Photos")
    st.markdown('<div class="subtitle">Every photo in your gallery, gathered from all nested folders.</div>', unsafe_allow_html=True)
else:
    st.title(current_name)
    crumbs = ["All Photos"] + [x["name"] for x in st.session_state.folder_breadcrumb]
    st.markdown('<div class="subtitle">' + "  /  ".join(crumbs) + '</div>', unsafe_allow_html=True)

if not is_root:
    if st.button("← All Photos"):
        st.session_state.current_folder_id = root_id
        st.session_state.current_folder_name = "All Photos"
        st.session_state.folder_breadcrumb = []
        st.rerun()

# Search and sort controls
c1, c2, c3 = st.columns([2.6, 1.15, 1.0])
with c1:
    search = st.text_input("Search", placeholder="Search photos by filename…", label_visibility="collapsed")
with c2:
    sort = st.selectbox("Sort", ["Newest first", "Oldest first", "Name A–Z", "Name Z–A"], label_visibility="collapsed")
with c3:
    density = st.selectbox("View", ["Comfortable", "Dense"], label_visibility="collapsed")

try:
    # Root view recursively includes nested-folder photos; a folder view includes its own descendants.
    images = drive.list_images_recursive(current_id, query=search.strip())
    child_folders = drive.list_folders(current_id)
    if sort == "Newest first":
        images.sort(key=lambda x:x.get("modifiedTime",""), reverse=True)
    elif sort == "Oldest first":
        images.sort(key=lambda x:x.get("modifiedTime",""))
    elif sort == "Name A–Z":
        images.sort(key=lambda x:x.get("name","").casefold())
    else:
        images.sort(key=lambda x:x.get("name","").casefold(), reverse=True)
except Exception as exc:
    st.error(f"Could not read this Drive folder: {exc}")
    st.stop()

# Album/folder tiles are clearly separated from photos.
if child_folders:
    st.markdown('<div class="section-title">Albums</div>', unsafe_allow_html=True)
    folder_cols = st.columns(5 if density == "Dense" else 4)
    for i, folder in enumerate(child_folders):
        with folder_cols[i % len(folder_cols)]:
            with st.container(border=True):
                st.markdown(f"📁 **{folder['name']}**")
                st.caption("Folder")
                if st.button("Open album", key=f"album_{folder['id']}", use_container_width=True):
                    st.session_state.current_folder_id = folder["id"]
                    st.session_state.current_folder_name = folder["name"]
                    st.session_state.folder_breadcrumb = st.session_state.folder_breadcrumb + [{"id":folder["id"],"name":folder["name"]}]
                    st.rerun()

st.markdown('<div class="section-title">Photos</div>', unsafe_allow_html=True)
st.caption(f"{len(images)} photos" + (f" · Searching within {current_name}" if search else ""))

# Paginate before downloading bytes. 48 per page is a practical balance for Streamlit Cloud.
page_size = 48
page_count = max(1, math.ceil(len(images) / page_size))
if "photo_page" not in st.session_state:
    st.session_state.photo_page = 1
filter_key = (current_id, search, sort)
if st.session_state.get("photo_filter_key") != filter_key:
    st.session_state.photo_filter_key = filter_key
    st.session_state.photo_page = 1
st.session_state.photo_page = min(st.session_state.photo_page, page_count)
offset = (st.session_state.photo_page - 1) * page_size
visible = images[offset:offset + page_size]

if not visible:
    st.info("No photos found here. Add photos or folders directly in Google Drive.")
else:
    payload_items = []
    status = st.empty()
    for i, file in enumerate(visible):
        try:
            raw = drive.download_bytes(file["id"])
            mime = file.get("mimeType") or "image/jpeg"
            payload_items.append({
                "id":file["id"],
                "name":file.get("name","Photo"),
                "date":file.get("modifiedTime","")[:10],
                "size":int(file.get("size",0) or len(raw)),
                "mime":mime,
                "src":"data:"+mime+";base64,"+base64.b64encode(raw).decode("ascii"),
            })
        except Exception as exc:
            st.warning(f"Preview unavailable for {file.get('name','photo')}: {exc}")
        status.caption(f"Loading previews {i+1} of {len(visible)}…")
    status.empty()

    if payload_items:
        data = json.dumps(payload_items, ensure_ascii=True).replace("</","<\\/")
        cols = 6 if density == "Dense" else 5
        html = r"""
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;background:transparent;color:#1d1d1f;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.grid{display:grid;grid-template-columns:repeat(__COLS__,minmax(0,1fr));gap:12px}
.photo{position:relative;overflow:hidden;border-radius:13px;background:#e8e8ed;aspect-ratio:1/1;cursor:zoom-in;transition:transform .18s,box-shadow .18s}
.photo:hover{transform:scale(1.018);box-shadow:0 8px 22px #0002}
.photo img{width:100%;height:100%;object-fit:cover;display:block}
.photo .caption{position:absolute;left:0;right:0;bottom:0;padding:25px 9px 8px;color:white;font-size:11px;font-weight:600;background:linear-gradient(transparent,#0008);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:0;transition:opacity .15s}
.photo:hover .caption{opacity:1}
.viewer{display:none;position:fixed;inset:0;z-index:9999;background:rgba(250,250,252,.98);align-items:center;justify-content:center;flex-direction:column;padding:24px}
.viewer.open{display:flex}
.viewer img{max-width:92vw;max-height:80vh;object-fit:contain;box-shadow:0 8px 35px #0001}
.vtop{position:absolute;top:14px;left:22px;right:22px;display:flex;justify-content:space-between;color:#666;font-size:13px}
.close{position:absolute;right:18px;top:44px;border:0;background:#e9e9ee;color:#333;font-size:24px;border-radius:50%;width:40px;height:40px;cursor:pointer}
.nav{position:absolute;top:50%;transform:translateY(-50%);width:42px;height:42px;border:0;border-radius:50%;background:#e9e9ee;color:#333;font-size:24px;cursor:pointer}.prev{left:18px}.next{right:18px}
.vbottom{position:absolute;bottom:16px;display:flex;align-items:center;gap:14px;color:#333;font-size:13px;flex-wrap:wrap;justify-content:center}
.dl{color:#06c;text-decoration:none;font-weight:600}
@media(max-width:1200px){.grid{grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}}
@media(max-width:850px){.grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:7px}}
@media(max-width:560px){.grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}.photo{border-radius:8px}}
</style></head><body>
<div class="grid" id="grid"></div>
<div class="viewer" id="viewer">
 <div class="vtop"><span id="counter"></span><span>← → to navigate · Esc to close</span></div>
 <button class="close" id="close" aria-label="Close">×</button>
 <button class="nav prev" id="prev" aria-label="Previous">‹</button>
 <img id="full" alt="Photo preview">
 <button class="nav next" id="next" aria-label="Next">›</button>
 <div class="vbottom"><span id="title"></span><a class="dl" id="download" download>Download original ↓</a></div>
</div>
<script>
const items=__DATA__;let index=0;
const grid=document.getElementById('grid'),viewer=document.getElementById('viewer'),full=document.getElementById('full');
items.forEach((it,i)=>{
 const card=document.createElement('div');card.className='photo';
 const im=document.createElement('img');im.loading='lazy';im.src=it.src;im.alt=it.name;
 const cap=document.createElement('div');cap.className='caption';cap.textContent=it.name;
 card.append(im,cap);card.addEventListener('click',()=>open(i));grid.appendChild(card);
});
function render(){const it=items[index];full.src=it.src;document.getElementById('counter').textContent=(index+1)+' of '+items.length;document.getElementById('title').textContent=it.name;const dl=document.getElementById('download');dl.href=it.src;dl.download=it.name}
function open(i){index=i;viewer.classList.add('open');render()}
function close(){viewer.classList.remove('open')}
function move(n){index=(index+n+items.length)%items.length;render()}
document.getElementById('close').onclick=close;document.getElementById('prev').onclick=()=>move(-1);document.getElementById('next').onclick=()=>move(1);
viewer.addEventListener('click',e=>{if(e.target===viewer)close()});
document.addEventListener('keydown',e=>{if(!viewer.classList.contains('open'))return;if(e.key==='Escape')close();if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1)});
let sx=0,sy=0;viewer.addEventListener('touchstart',e=>{sx=e.touches[0].clientX;sy=e.touches[0].clientY},{passive:true});
viewer.addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-sx,dy=e.changedTouches[0].clientY-sy;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy))move(dx<0?1:-1)},{passive:true});
function setHeight(){const h=document.documentElement.scrollHeight;window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h},'*')}
window.addEventListener('load',setHeight);window.addEventListener('resize',setHeight);if(window.ResizeObserver)new ResizeObserver(setHeight).observe(document.body);setTimeout(setHeight,200);
</script></body></html>
""".replace("__COLS__", str(cols)).replace("__DATA__", data)
        # Dynamic frame height prevents a giant empty area; images are square tiles.
        rows = math.ceil(len(payload_items) / cols)
        components.html(html, height=max(250, rows * 190 + 35), scrolling=False)

if page_count > 1:
    p1,p2,p3=st.columns([1,2,1])
    with p1:
        if st.button("Previous",disabled=st.session_state.photo_page<=1,use_container_width=True):
            st.session_state.photo_page-=1;st.rerun()
    with p2:
        st.markdown(f"<div style='text-align:center;padding:.5rem;color:#777'>Page {st.session_state.photo_page} of {page_count}</div>",unsafe_allow_html=True)
    with p3:
        if st.button("Next",disabled=st.session_state.photo_page>=page_count,use_container_width=True):
            st.session_state.photo_page+=1;st.rerun()
