import base64
import json
import math
import streamlit as st
import streamlit.components.v1 as components

from backend.auth import require_login
from backend.drive import DriveGallery

st.set_page_config(page_title="My Private Gallery", page_icon="🖼️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.block-container{max-width:1800px;padding:1rem 1.25rem 2rem}
[data-testid="stAppViewContainer"]{background:linear-gradient(145deg,#10131b 0%,#192236 55%,#111722 100%)}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.03em}
section[data-testid="stSidebar"]{background:#111722}
div[data-testid="stSelectbox"] div[role="combobox"],div[data-testid="stTextInput"] input{border-radius:10px}
.hero{padding:1.05rem 1.35rem;border:1px solid #ffffff18;border-radius:17px;background:linear-gradient(110deg,#626cff27,#23c6a017);margin-bottom:.8rem}
.kicker{font-size:.68rem;letter-spacing:.15em;text-transform:uppercase;color:#b8c5df;font-weight:700}
.hero-title{font:800 clamp(1.45rem,2.4vw,2rem) Manrope;margin:.22rem 0}
.hero-sub{font-size:.86rem;color:#bdc8dc}
div[data-testid="stHorizontalBlock"]{gap:.65rem}
</style>
""", unsafe_allow_html=True)

require_login()

@st.cache_resource
def drive_client():
    return DriveGallery()

try:
    drive = drive_client()
    root_id = drive.root_id
except Exception as exc:
    st.error("Unable to connect to Google Drive.")
    st.code(str(exc))
    st.info("Check the service-account fields in Streamlit Secrets, confirm the root folder is shared with its client_email, and confirm Google Drive API is enabled.")
    if st.button("Retry connection"):
        st.rerun()
    st.stop()

st.markdown("""
<div class="hero">
  <div class="kicker">Your private collection</div>
  <div class="hero-title">All your images. One clean view.</div>
  <div class="hero-sub">Browse folders and subfolders, search filenames, and open any image in a swipeable full-screen viewer.</div>
</div>
""", unsafe_allow_html=True)

# Build a folder path using cascading selectors. Each level drills into the selected folder.
if "folder_path" not in st.session_state:
    st.session_state.folder_path = []

def change_folder(level, key):
    chosen = st.session_state.get(key)
    path = st.session_state.folder_path[:level]
    if chosen:
        path.append(chosen)
    st.session_state.folder_path = path

path = st.session_state.folder_path
parent_id = root_id
levels = []
try:
    root_folders = drive.list_folders(parent_id)
    folder_sets = [root_folders]
    current_folders = root_folders
    for depth in range(4):
        if not current_folders:
            break
        key = f"folder_level_{depth}"
        valid_ids = [f["id"] for f in current_folders]
        old_id = path[depth] if depth < len(path) else None
        if old_id not in valid_ids:
            old_id = None
        options = [None] + valid_ids
        names = {f["id"]: f["name"] for f in current_folders}
        selected_index = options.index(old_id)
        label = ["Folder", "Subfolder", "Subfolder 2", "Subfolder 3"][depth]
        selected_id = st.selectbox(
            label,
            options,
            index=selected_index,
            format_func=lambda x, names=names: "All items in root" if x is None and depth == 0 else ("Choose a folder…" if x is None else names.get(x, "Folder")),
            key=key,
            on_change=change_folder,
            args=(depth, key),
        )
        if selected_id is None:
            path = path[:depth]
            break
        if depth >= len(path) or path[depth] != selected_id:
            path = path[:depth] + [selected_id]
            st.session_state.folder_path = path
        parent_id = selected_id
        current_folders = drive.list_folders(parent_id)
    # If user navigated to a selected folder, load its children as subfolders.
    active_folder_id = path[-1] if path else root_id
    child_folders = drive.list_folders(active_folder_id)
except Exception as exc:
    st.error(f"Could not load Drive folders: {exc}")
    st.stop()

# Breadcrumb shows current location.
crumb_names = ["My Private Gallery"]
for fid in path:
    found = drive.get_folder(fid)
    if found:
        crumb_names.append(found["name"])
st.caption(" / ".join(crumb_names))

# Toolbar: search + sort + density + type.
t1, t2, t3, t4 = st.columns([2.2, 1.05, 1.0, 1.0])
with t1:
    query = st.text_input("Search files", placeholder="⌕  Search this folder by filename…", label_visibility="collapsed")
with t2:
    sort = st.selectbox("Sort", ["Newest", "Oldest", "Name A–Z", "Name Z–A"], label_visibility="collapsed")
with t3:
    density = st.selectbox("Grid size", ["Large", "Medium", "Small"], index=1, label_visibility="collapsed")
with t4:
    kind = st.selectbox("Show", ["All items", "Images only", "Folders only"], label_visibility="collapsed")

try:
    images = drive.list_images(active_folder_id, query=query.strip())
    if sort == "Newest":
        images.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
    elif sort == "Oldest":
        images.sort(key=lambda x: x.get("modifiedTime", ""))
    elif sort == "Name A–Z":
        images.sort(key=lambda x: x.get("name", "").casefold())
    else:
        images.sort(key=lambda x: x.get("name", "").casefold(), reverse=True)
    if kind == "Folders only":
        images = []
    if kind == "Images only":
        child_folders = []
except Exception as exc:
    st.error(f"Could not load images: {exc}")
    st.stop()

# Folder cards first, with clear navigation. Folder selection is handled by a simple button.
if kind != "Images only" and child_folders:
    st.markdown("**Folders**")
    folder_cols = st.columns(5)
    for i, folder in enumerate(child_folders):
        with folder_cols[i % 5]:
            with st.container(border=True):
                st.markdown(f"📁 **{folder['name']}**")
                st.caption("Open folder")
                if st.button("Open →", key=f"open_folder_{folder['id']}", use_container_width=True):
                    st.session_state.folder_path = path + [folder["id"]]
                    st.rerun()

# Load a moderate number of images to keep rendering and memory usage responsive.
page_size = 48
total = len(images)
pages = max(1, math.ceil(total / page_size))
if "image_page" not in st.session_state:
    st.session_state.image_page = 1
filter_sig = (active_folder_id, query, sort, kind)
if st.session_state.get("image_filter_sig") != filter_sig:
    st.session_state.image_filter_sig = filter_sig
    st.session_state.image_page = 1
st.session_state.image_page = min(st.session_state.image_page, pages)
start = (st.session_state.image_page - 1) * page_size
selected_images = images[start:start + page_size]

st.markdown(f"**Images** · {total} found", unsafe_allow_html=True)
if not selected_images:
    st.info("No images in this folder. Open a subfolder or add images directly in Google Drive.")
else:
    gallery = []
    progress = st.empty()
    for i, item in enumerate(selected_images):
        try:
            raw = drive.download_bytes(item["id"])
            mime = item.get("mimeType") or "image/jpeg"
            gallery.append({
                "id": item["id"],
                "name": item.get("name", "Image"),
                "date": item.get("modifiedTime", "")[:10],
                "size": int(item.get("size", 0) or len(raw)),
                "mime": mime,
                "src": "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii"),
            })
        except Exception as exc:
            st.warning(f"Could not load {item.get('name','image')}: {exc}")
        progress.caption(f"Loading image previews {i+1}/{len(selected_images)}…")
    progress.empty()

    if gallery:
        payload = json.dumps(gallery, ensure_ascii=True).replace("</", "<\\/")
        columns = {"Large": 4, "Medium": 6, "Small": 8}[density]
        # The embedded grid fills the available page width; viewer opens only on image click.
        html = r"""
<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;background:transparent;color:#f2f5ff;font-family:Arial,sans-serif}
.grid{display:grid;grid-template-columns:repeat(__COLS__,minmax(0,1fr));gap:12px}
.card{min-width:0;border:1px solid #ffffff15;background:#ffffff08;border-radius:12px;overflow:hidden;transition:transform .16s,border-color .16s;cursor:pointer}
.card:hover{transform:translateY(-3px);border-color:#9aa9ff88}
.thumb{width:100%;aspect-ratio:1/1;background:#0b101a;display:flex;align-items:center;justify-content:center;overflow:hidden}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.info{padding:8px 9px 9px}.name{font-size:12px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.meta{font-size:10px;color:#aab6cc;margin-top:4px}
.viewer{display:none;position:fixed;inset:0;z-index:1000;background:rgba(3,6,12,.97);align-items:center;justify-content:center;flex-direction:column;padding:18px}
.viewer.open{display:flex}.viewer img{max-width:94vw;max-height:78vh;object-fit:contain}
.vtop{position:absolute;top:12px;left:18px;right:18px;display:flex;justify-content:space-between;color:#dbe4f7;font-size:13px}
.close{position:absolute;right:18px;top:40px;border:0;background:#ffffff18;color:white;font-size:26px;border-radius:50%;width:42px;height:42px;cursor:pointer}
.nav{position:absolute;top:50%;transform:translateY(-50%);width:42px;height:42px;border:1px solid #ffffff55;border-radius:50%;background:#182235d9;color:white;font-size:25px;cursor:pointer}.prev{left:16px}.next{right:16px}
.vbottom{position:absolute;bottom:14px;left:12px;right:12px;display:flex;align-items:center;justify-content:center;gap:10px;color:#dce5f7;font-size:12px;flex-wrap:wrap}
.dl{color:white;text-decoration:none;border:1px solid #ffffff44;padding:8px 12px;border-radius:9px;background:#ffffff13}
@media(max-width:1200px){.grid{grid-template-columns:repeat(5,minmax(0,1fr))}}
@media(max-width:850px){.grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}}
@media(max-width:550px){.grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.info{padding:6px}.name{font-size:10px}}
</style></head><body>
<div class="grid" id="grid"></div>
<div class="viewer" id="viewer">
 <div class="vtop"><span id="count"></span><span>Swipe · ← → · Esc to close</span></div>
 <button class="close" id="close">×</button>
 <button class="nav prev" id="prev">‹</button>
 <img id="full" alt="Full image">
 <button class="nav next" id="next">›</button>
 <div class="vbottom"><span id="title"></span><a class="dl" id="download" download>↓ Download original</a></div>
</div>
<script>
const items=__DATA__;let index=0;
const grid=document.getElementById('grid'),viewer=document.getElementById('viewer'),full=document.getElementById('full');
items.forEach((it,i)=>{
 const card=document.createElement('div');card.className='card';
 const thumb=document.createElement('div');thumb.className='thumb';
 const im=document.createElement('img');im.loading='lazy';im.src=it.src;im.alt=it.name;thumb.appendChild(im);
 const info=document.createElement('div');info.className='info';
 const name=document.createElement('div');name.className='name';name.textContent=it.name;
 const meta=document.createElement('div');meta.className='meta';meta.textContent=(it.date||'')+(it.size?' · '+Math.round(it.size/1024)+' KB':'');
 info.append(name,meta);card.append(thumb,info);card.onclick=()=>open(i);grid.appendChild(card);
});
function render(){const it=items[index];full.src=it.src;document.getElementById('count').textContent=(index+1)+' / '+items.length;document.getElementById('title').textContent=it.name;const dl=document.getElementById('download');dl.href=it.src;dl.download=it.name}
function open(i){index=i;viewer.classList.add('open');render()}
function close(){viewer.classList.remove('open')}
function move(d){index=(index+d+items.length)%items.length;render()}
document.getElementById('close').onclick=close;document.getElementById('prev').onclick=()=>move(-1);document.getElementById('next').onclick=()=>move(1);
viewer.addEventListener('click',e=>{if(e.target===viewer)close()});
document.addEventListener('keydown',e=>{if(!viewer.classList.contains('open'))return;if(e.key==='Escape')close();if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1)});
let sx=0,sy=0;viewer.addEventListener('touchstart',e=>{sx=e.touches[0].clientX;sy=e.touches[0].clientY},{passive:true});
viewer.addEventListener('touchend',e=>{let dx=e.changedTouches[0].clientX-sx,dy=e.changedTouches[0].clientY-sy;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy))move(dx<0?1:-1)},{passive:true});
// Tell Streamlit the actual responsive grid height, avoiding a fixed-height blank area or clipped rows.
function reportHeight(){const h=Math.max(document.body.scrollHeight,document.documentElement.scrollHeight);window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:h},'*')}
window.addEventListener('load',reportHeight);window.addEventListener('resize',reportHeight);
if(window.ResizeObserver){new ResizeObserver(reportHeight).observe(document.body)}
setTimeout(reportHeight,100);setTimeout(reportHeight,500);
</script></body></html>
""".replace("__COLS__", str(columns)).replace("__DATA__", payload)
        rows = math.ceil(len(gallery) / columns)
        height = max(240, rows * 205 + 20)
        components.html(html, height=height, scrolling=False)

if pages > 1:
    a, b, c = st.columns([1, 2, 1])
    with a:
        if st.button("← Previous", disabled=st.session_state.image_page <= 1, use_container_width=True):
            st.session_state.image_page -= 1
            st.rerun()
    with b:
        st.markdown(f"<div style='text-align:center;padding:.5rem;color:#aebbd2'>Page {st.session_state.image_page} of {pages}</div>", unsafe_allow_html=True)
    with c:
        if st.button("Next →", disabled=st.session_state.image_page >= pages, use_container_width=True):
            st.session_state.image_page += 1
            st.rerun()

with st.sidebar:
    st.markdown("### 🖼️ My Gallery")
    st.caption("Password-protected · Google Drive")
    st.divider()
    st.link_button("Open Google Drive", "https://drive.google.com/drive/my-drive", use_container_width=True)
    if st.button("Refresh gallery", use_container_width=True):
        st.rerun()
    st.caption("Create folders and manage files directly in Google Drive.")
