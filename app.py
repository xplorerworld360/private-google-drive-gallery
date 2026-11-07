import base64
import json
import math
import streamlit as st
import streamlit.components.v1 as components

from backend.auth import require_login
from backend.drive import DriveGallery

st.set_page_config(page_title="My Private Gallery", page_icon="🖼️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.block-container{max-width:1500px;padding-top:1.15rem;padding-bottom:2.5rem}
[data-testid="stAppViewContainer"]{background:linear-gradient(145deg,#10131b 0%,#182033 55%,#111722 100%)}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.035em}
section[data-testid="stSidebar"]{background:#111722;border-right:1px solid #ffffff12}
.hero{padding:1.35rem 1.55rem;border:1px solid #ffffff18;border-radius:20px;background:linear-gradient(115deg,#626cff2b,#23c6a017);margin-bottom:1rem}
.eyebrow{font-size:.7rem;text-transform:uppercase;letter-spacing:.16em;color:#aeb9d2;font-weight:700}
.hero-title{font-family:'Manrope',sans-serif;font-size:clamp(1.65rem,3vw,2.25rem);font-weight:800;line-height:1.12;margin:.35rem 0}
.hero-sub{color:#b7c1d4;font-size:.9rem}
.stats{display:flex;gap:.55rem;flex-wrap:wrap;margin-top:.9rem}
.stat{font-size:.78rem;color:#dce4f5;padding:.38rem .7rem;border:1px solid #ffffff18;border-radius:999px;background:#ffffff09}
div[data-testid="stSelectbox"] div[role="combobox"],div[data-testid="stTextInput"] input{border-radius:12px}
div.stButton>button{border-radius:11px}
</style>
""", unsafe_allow_html=True)

require_login()

try:
    drive = DriveGallery()
    albums = drive.list_albums()
except Exception as exc:
    st.error("Unable to connect to Google Drive.")
    st.code(str(exc))
    st.markdown("""
    **Try these checks:**
    1. Confirm the service-account details in Streamlit Secrets are copied exactly from the downloaded JSON key.
    2. Confirm the root Drive folder is shared with the service-account email.
    3. Confirm Google Drive API is enabled in the same Google Cloud project.
    4. If the error contains `SSL: RECORD_LAYER_FAILURE`, use the included `runtime.txt` (Python 3.12), updated `certifi` and retry-enabled HTTPS transport. This is a TLS/network connection issue, not normally a folder permission error.
    """)
    if st.button("Retry Google Drive connection"):
        st.rerun()
    st.stop()

albums_by_name = {a["name"]: a for a in albums}
album_names = ["All albums"] + sorted(albums_by_name, key=str.casefold)

# Minimal header: no oversized dashboard cards or sidebar clutter.
st.markdown("""
<div class="hero">
  <div class="eyebrow">Your private collection</div>
  <div class="hero-title">A calmer way to explore your gallery.</div>
  <div class="hero-sub">Choose an album, search, then swipe through your images. Tap any image to open the immersive viewer.</div>
</div>
""", unsafe_allow_html=True)

control1, control2, control3 = st.columns([1.15, 2.1, 1.05])
with control1:
    selected_album = st.selectbox("Album", album_names, label_visibility="collapsed")
with control2:
    search_text = st.text_input("Search images", placeholder="⌕  Search by filename…", label_visibility="collapsed")
with control3:
    sort_by = st.selectbox("Sort", ["Newest first", "Oldest first", "Name A–Z", "Name Z–A"], label_visibility="collapsed")

album_id = None if selected_album == "All albums" else albums_by_name[selected_album]["id"]

try:
    images = drive.list_images(album_id=album_id, query=search_text.strip())
except Exception as exc:
    st.error(f"Could not list images: {exc}")
    st.stop()

if sort_by == "Newest first":
    images.sort(key=lambda x: x.get("modifiedTime", ""), reverse=True)
elif sort_by == "Oldest first":
    images.sort(key=lambda x: x.get("modifiedTime", ""))
elif sort_by == "Name A–Z":
    images.sort(key=lambda x: x.get("name", "").casefold())
else:
    images.sort(key=lambda x: x.get("name", "").casefold(), reverse=True)

# Keep the gallery lightweight: only fetch a small page of images at a time.
page_size = 12
total = len(images)
pages = max(1, math.ceil(total / page_size))
if "gallery_page" not in st.session_state:
    st.session_state.gallery_page = 1
st.session_state.gallery_page = min(st.session_state.gallery_page, pages)

# Reset to first page when filters change.
filter_signature = (selected_album, search_text, sort_by)
if st.session_state.get("filter_signature") != filter_signature:
    st.session_state.filter_signature = filter_signature
    st.session_state.gallery_page = 1

start = (st.session_state.gallery_page - 1) * page_size
page_items = images[start:start + page_size]

if "gallery_favourites" not in st.session_state:
    st.session_state.gallery_favourites = set()

header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown(f"**{total} images**  <span style='color:#9eabc3'>· {selected_album}</span>", unsafe_allow_html=True)
with header_right:
    show_favourites = st.toggle("Favourites", value=False)

if show_favourites:
    page_items = [item for item in page_items if item["id"] in st.session_state.gallery_favourites]

if not page_items:
    st.info("No images found in this selection. Add images or folders directly in Google Drive, then refresh.")
else:
    gallery_data = []
    errors = []
    progress = st.empty()
    for index, item in enumerate(page_items):
        try:
            raw = drive.download_bytes(item["id"])
            encoded = base64.b64encode(raw).decode("ascii")
            mime = item.get("mimeType") or "image/jpeg"
            gallery_data.append({
                "id": item["id"],
                "name": item.get("name", "Image"),
                "date": item.get("modifiedTime", "")[:10],
                "size": int(item.get("size", 0) or len(raw)),
                "mime": mime,
                "src": f"data:{mime};base64,{encoded}",
                "favourite": item["id"] in st.session_state.gallery_favourites,
            })
        except Exception as exc:
            errors.append(f"{item.get('name','Image')}: {exc}")
        progress.caption(f"Preparing gallery {index + 1}/{len(page_items)}…")
    progress.empty()

    if gallery_data:
        # JSON is embedded as data, and rendered with DOM textContent to avoid HTML injection.
        payload = json.dumps(gallery_data, ensure_ascii=True).replace("</", "<\\/")
        html = r"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;background:transparent;color:#f3f6ff;font-family:Arial,sans-serif}
.shell{border:1px solid rgba(255,255,255,.09);border-radius:20px;background:linear-gradient(145deg,rgba(255,255,255,.055),rgba(255,255,255,.025));padding:14px;overflow:hidden}
.topline{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:0 2px 12px;color:#aebbd2;font-size:12px}
.stage{height:430px;position:relative;border-radius:16px;background:#090d15;display:flex;align-items:center;justify-content:center;overflow:hidden;touch-action:pan-y;cursor:zoom-in}
.stage img{width:100%;height:100%;object-fit:contain;transition:opacity .16s ease}
.nav{position:absolute;top:50%;transform:translateY(-50%);width:42px;height:42px;border:1px solid #ffffff40;border-radius:50%;background:#101725c9;color:white;font-size:24px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px)}
.nav:hover{background:#5364d8}
.prev{left:12px}.next{right:12px}
.counter{position:absolute;right:13px;top:13px;padding:6px 10px;border-radius:30px;background:#0b101bc9;color:#e8edfa;font-size:12px}
.caption{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 3px 10px}
.name{font-weight:700;font-size:14px;overflow-wrap:anywhere}
.meta{color:#9eabc3;font-size:12px;margin-top:4px}
.actions{display:flex;gap:8px;align-items:center}
.action{display:inline-flex;align-items:center;justify-content:center;text-decoration:none;border:1px solid #ffffff26;background:#ffffff0b;color:#eaf0ff;border-radius:10px;padding:8px 12px;font-size:12px;cursor:pointer}
.action:hover{background:#ffffff18}
.thumbs{display:flex;gap:9px;overflow-x:auto;padding:8px 2px 3px;scrollbar-width:thin;scrollbar-color:#66728d transparent}
.thumb{flex:0 0 76px;height:76px;border-radius:11px;overflow:hidden;border:2px solid transparent;opacity:.62;cursor:pointer;background:#0b101b}
.thumb img{width:100%;height:100%;object-fit:cover}
.thumb.active{border-color:#9ba9ff;opacity:1}
.empty{height:430px;display:grid;place-items:center;color:#aebbd2}
.lightbox{display:none;position:fixed;inset:0;z-index:99;background:rgba(3,6,12,.97);align-items:center;justify-content:center;flex-direction:column;padding:18px}
.lightbox.open{display:flex}
.lightbox img{max-width:94%;max-height:78%;object-fit:contain}
.close{position:absolute;top:15px;right:18px;font-size:30px;color:white;background:transparent;border:0;cursor:pointer}
.lightbox .nav{position:fixed}
.lightbox .prev{left:18px}.lightbox .next{right:18px}
.lightcap{color:#dce5f7;margin-top:14px;text-align:center;font-size:13px}
@media(max-width:650px){.shell{padding:9px}.stage{height:58vh;min-height:280px;max-height:520px}.thumb{flex-basis:62px;height:62px}.caption{align-items:flex-start;flex-direction:column}.actions{width:100%}.action{flex:1}.nav{width:36px;height:36px}}
</style>
</head>
<body>
<div class="shell">
  <div class="topline"><span>COLLECTION VIEWER</span><span id="hint">Swipe · Use ← → · Tap image to enlarge</span></div>
  <div class="stage" id="stage">
    <img id="mainImage" alt="Gallery image">
    <button class="nav prev" id="prev" aria-label="Previous image">‹</button>
    <button class="nav next" id="next" aria-label="Next image">›</button>
    <div class="counter" id="counter"></div>
  </div>
  <div class="caption">
    <div><div class="name" id="imageName"></div><div class="meta" id="imageMeta"></div></div>
    <div class="actions"><a class="action" id="download" download>↓ Download original</a><button class="action" id="favourite">♡ Favourite</button><button class="action" id="open">⛶ Full view</button></div>
  </div>
  <div class="thumbs" id="thumbs"></div>
</div>
<div class="lightbox" id="lightbox">
  <button class="close" id="close" aria-label="Close">×</button>
  <button class="nav prev" id="lbPrev" aria-label="Previous image">‹</button>
  <img id="largeImage" alt="Full size image">
  <button class="nav next" id="lbNext" aria-label="Next image">›</button>
  <div class="lightcap" id="lightcap"></div>
</div>
<script>
const items = __PAYLOAD__;
let current = 0;
const mainImage=document.getElementById('mainImage');
const largeImage=document.getElementById('largeImage');
const nameEl=document.getElementById('imageName');
const metaEl=document.getElementById('imageMeta');
const counter=document.getElementById('counter');
const download=document.getElementById('download');
const favourite=document.getElementById('favourite');
const thumbs=document.getElementById('thumbs');
const lightbox=document.getElementById('lightbox');
const lightcap=document.getElementById('lightcap');
const stage=document.getElementById('stage');
function render(){
 const item=items[current];
 mainImage.style.opacity='0.25';
 setTimeout(()=>{mainImage.src=item.src;mainImage.style.opacity='1'},60);
 nameEl.textContent=item.name;
 metaEl.textContent=(item.date||'')+(item.size?' · '+(item.size/1024).toFixed(0)+' KB':'');
 counter.textContent=(current+1)+' / '+items.length;
 download.href=item.src;download.download=item.name;
 favourite.textContent=item.favourite?'♥ Saved':'♡ Favourite';
 [...thumbs.children].forEach((el,i)=>el.classList.toggle('active',i===current));
 if(lightbox.classList.contains('open')){largeImage.src=item.src;lightcap.textContent=item.name+' · '+(current+1)+' / '+items.length}
}
function go(delta){current=(current+delta+items.length)%items.length;render();const t=thumbs.children[current];if(t)t.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}
items.forEach((item,i)=>{
 const button=document.createElement('button');button.className='thumb';button.type='button';button.title=item.name;
 const image=document.createElement('img');image.src=item.src;image.alt=item.name;button.appendChild(image);
 button.addEventListener('click',()=>{current=i;render()});thumbs.appendChild(button);
});
document.getElementById('prev').onclick=()=>go(-1);
document.getElementById('next').onclick=()=>go(1);
document.getElementById('lbPrev').onclick=()=>go(-1);
document.getElementById('lbNext').onclick=()=>go(1);
function openViewer(){lightbox.classList.add('open');render()}
function closeViewer(){lightbox.classList.remove('open')}
mainImage.onclick=openViewer;document.getElementById('open').onclick=openViewer;
document.getElementById('close').onclick=closeViewer;
lightbox.addEventListener('click',e=>{if(e.target===lightbox)closeViewer()});
favourite.onclick=()=>{items[current].favourite=!items[current].favourite;render()};
let touchX=0,touchY=0;
function touchStart(e){const t=e.touches[0];touchX=t.clientX;touchY=t.clientY}
function touchEnd(e){if(!touchX)return;const t=e.changedTouches[0];const dx=t.clientX-touchX;const dy=t.clientY-touchY;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)*1.2)go(dx<0?1:-1);touchX=0;touchY=0}
[stage,lightbox].forEach(el=>{el.addEventListener('touchstart',touchStart,{passive:true});el.addEventListener('touchend',touchEnd,{passive:true})});
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight')go(1);if(e.key==='ArrowLeft')go(-1);if(e.key==='Escape')closeViewer()});
render();
</script>
</body>
</html>
""".replace("__PAYLOAD__", payload)

        # Height is fixed; the carousel itself stays compact and responsive.
        components.html(html, height=690, scrolling=False)

    if errors:
        with st.expander(f"{len(errors)} image(s) could not be loaded"):
            for error in errors:
                st.write(error)

if pages > 1:
    left, center, right = st.columns([1, 2, 1])
    with left:
        if st.button("← Previous page", disabled=st.session_state.gallery_page <= 1, use_container_width=True):
            st.session_state.gallery_page -= 1
            st.rerun()
    with center:
        st.markdown(f"<div style='text-align:center;padding:.55rem;color:#aebbd2'>Page {st.session_state.gallery_page} of {pages}</div>", unsafe_allow_html=True)
    with right:
        if st.button("Next page →", disabled=st.session_state.gallery_page >= pages, use_container_width=True):
            st.session_state.gallery_page += 1
            st.rerun()

with st.sidebar:
    st.markdown("### 🖼️ My Gallery")
    st.caption("Password-protected · Google Drive")
    st.divider()
    st.link_button("Open Google Drive", "https://drive.google.com/drive/my-drive", use_container_width=True)
    if st.button("Refresh gallery", use_container_width=True):
        st.rerun()
    st.caption("Manage folders and files directly in Google Drive. This gallery only reads and displays them.")
