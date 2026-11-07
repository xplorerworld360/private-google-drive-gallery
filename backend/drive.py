import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload,MediaIoBaseUpload

FOLDER="application/vnd.google-apps.folder"
class Drive:
    def __init__(self,credentials):
        self.api=build("drive","v3",credentials=credentials,cache_discovery=False)
        self.root=st_root_id()
    def _list(self,q):
        out=[]; token=None
        while True:
            r=self.api.files().list(q=q,pageSize=1000,pageToken=token,orderBy="name",
              fields="nextPageToken,files(id,name,mimeType,modifiedTime,size,parents)",
              supportsAllDrives=True,includeItemsFromAllDrives=True).execute()
            out+=r.get("files",[]); token=r.get("nextPageToken")
            if not token: return out
    def albums(self):
        return self._list(f"'{self.root}' in parents and mimeType='{FOLDER}' and trashed=false")
    def images(self,album_id=None,query=""):
        parents=[album_id] if album_id else [a["id"] for a in self.albums()]
        out=[]
        for p in parents:
            q=f"'{p}' in parents and mimeType contains 'image/' and trashed=false"
            if query: q+=f" and name contains '{query.replace(chr(39), chr(92)+chr(39))}'"
            out+=self._list(q)
        return sorted(out,key=lambda x:x["name"].lower())
    def download(self,file_id):
        req=self.api.files().get_media(fileId=file_id,supportsAllDrives=True)
        buf=io.BytesIO(); dl=MediaIoBaseDownload(buf,req); done=False
        while not done: _,done=dl.next_chunk()
        return buf.getvalue()
    def upload(self,album_id,name,data,mime):
        media=MediaIoBaseUpload(io.BytesIO(data),mimetype=mime,resumable=True)
        return self.api.files().create(body={"name":name,"parents":[album_id]},media_body=media,fields="id,name").execute()
    def create_album(self,name):
        return self.api.files().create(body={"name":name,"mimeType":FOLDER,"parents":[self.root]},fields="id,name").execute()
    def rename(self,file_id,name):
        return self.api.files().update(fileId=file_id,body={"name":name},fields="id,name").execute()
    def delete(self,file_id):
        self.api.files().delete(fileId=file_id).execute()

def st_root_id():
    import streamlit as st
    return st.secrets["google_oauth"]["root_folder_id"]
