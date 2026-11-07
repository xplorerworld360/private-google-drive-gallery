import streamlit as st
from backend.auth import get_credentials, login, sidebar
from backend.drive import Drive

st.set_page_config(page_title="My Gallery", page_icon="🖼️", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.block-container{max-width:1550px;padding-top:1.4rem}
[data-testid="stAppViewContainer"]{background:linear-gradient(145deg,#10131b,#171d2a 55%,#11151e)}
[data-testid="stHeader"]{background:transparent}
h1,h2,h3{font-family:'Manrope',sans-serif;letter-spacing:-.035em}
.hero{padding:1.5rem;border:1px solid #ffffff18;border-radius:22px;background:linear-gradient(120deg,#626cff30,#24c4a018);margin-bottom:1.2rem}
.eyebrow{font-size:.75rem;letter-spacing:.15em;text-transform:uppercase;color:#aeb9d2;font-weight:700}
.hero-title{font:800 2.15rem Manrope;margin:.35rem 0}
.hero-sub,.muted{color:#aeb9cc}
.metric{padding:1rem;border:1px solid #ffffff18;border-radius:16px;background:#ffffff08}
.metric small{color:#aeb9cc}.metric strong{font:800 1.55rem Manrope;display:block}
div[data-testid="stImage"] img{border-radius:14px;object-fit:cover}
section[data-testid="stSidebar"]{background:#111722}
</style>""", unsafe_allow_html=True)

creds = get_credentials()
if not creds:
    login()
    st.stop()
sidebar()
drive = Drive(creds)
albums = drive.albums()
images_all = drive.images()
st.markdown('<div class="hero"><div class="eyebrow">Your personal cloud collection</div><div class="hero-title">Your gallery, beautifully organised.</div><div class="hero-sub">Browse albums, discover favourites and manage your collection directly in your own Google Drive.</div></div>', unsafe_allow_html=True)
a,b,c,d = st.columns(4)
for col,label,value in [(a,"ALBUMS",len(albums)),(b,"IMAGES",len(images_all)),(c,"STORAGE",f"{sum(int(x.get('size',0) or 0) for x in images_all)/1048576:.1f} MB"),(d,"ACCOUNT",st.session_state.get("email","Google"))]:
    col.markdown(f'<div class="metric"><small>{label}</small><strong>{value}</strong></div>',unsafe_allow_html=True)
st.write("")
x,y=st.columns([3,1])
x.subheader("Explore your collection")
y.page_link("pages/1_Admin.py",label="Open Admin Studio →",icon="⚙️")
f1,f2,f3=st.columns([2,2,1])
album_names=["All albums"]+[z["name"] for z in albums]
selected=f1.selectbox("Album",album_names,label_visibility="collapsed")
query=f2.text_input("Search",placeholder="⌕  Search filenames…",label_visibility="collapsed")
sort=f3.selectbox("Sort",["Newest","Oldest","Name A–Z","Name Z–A"],label_visibility="collapsed")
album_id=None if selected=="All albums" else next(z["id"] for z in albums if z["name"]==selected)
items=drive.images(album_id,query.strip())
if sort=="Newest": items.sort(key=lambda z:z.get("modifiedTime",""),reverse=True)
elif sort=="Oldest": items.sort(key=lambda z:z.get("modifiedTime",""))
elif sort=="Name A–Z": items.sort(key=lambda z:z["name"].lower())
else: items.sort(key=lambda z:z["name"].lower(),reverse=True)
st.caption(f"Showing {len(items)} image(s) · {selected}")
density=st.segmented_control("Layout",["Comfortable","Compact"],default="Comfortable",label_visibility="collapsed") or "Comfortable"
n=5 if density=="Compact" else 4
for start in range(0,len(items),n):
    for col,item in zip(st.columns(n,gap="medium"),items[start:start+n]):
        with col:
            try:
                data=drive.download(item["id"])
                st.image(data,use_container_width=True)
                st.markdown(f"**{item['name']}**")
                st.caption(f"{item.get('modifiedTime','')[:10]} · {int(item.get('size',0) or 0)/1024:.0f} KB")
                st.download_button("↓ Download",data,file_name=item["name"],mime=item.get("mimeType","image/jpeg"),key="dl"+item["id"],use_container_width=True)
            except Exception as e: st.warning(f"Preview unavailable: {e}")
if not items: st.info("No images found. Upload images from Admin Studio.")
st.divider()
st.caption("Your images remain in your Google Drive. This app does not make your Drive folders public.")
