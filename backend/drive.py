import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

READONLY_SCOPE=["https://www.googleapis.com/auth/drive.readonly"]
FILES_URL="https://www.googleapis.com/drive/v3/files"
FOLDER_MIME="application/vnd.google-apps.folder"

class DriveGallery:
    def __init__(self):
        info=dict(st.secrets["gdrive_service_account"])
        credentials=service_account.Credentials.from_service_account_info(info,scopes=READONLY_SCOPE)
        self.session=AuthorizedSession(credentials)
        retry=Retry(total=4,connect=4,read=3,status=3,backoff_factor=1,
                    status_forcelist=(429,500,502,503,504),
                    allowed_methods=frozenset(["GET"]),raise_on_status=False)
        adapter=HTTPAdapter(max_retries=retry,pool_connections=10,pool_maxsize=10)
        self.session.mount("https://",adapter)
        self.root_id=str(st.secrets["gdrive_root_folder_id"]).strip()
        if not self.root_id: raise ValueError("gdrive_root_folder_id is empty")

    def _get(self,url,params=None,stream=False):
        try:
            response=self.session.get(url,params=params,timeout=(15,90),stream=stream)
            if response.status_code>=400:
                try: detail=response.json().get("error",{}).get("message",response.text)
                except Exception: detail=response.text
                raise RuntimeError(f"Google Drive API HTTP {response.status_code}: {detail}")
            return response
        except requests.exceptions.SSLError as exc:
            raise RuntimeError(f"Google TLS/SSL connection failed: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Google Drive network error: {exc}") from exc

    def _list(self,q):
        out=[];token=None
        while True:
            params={"q":q,"pageSize":1000,"orderBy":"name",
                    "fields":"nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,webViewLink)",
                    "supportsAllDrives":"true","includeItemsFromAllDrives":"true"}
            if token: params["pageToken"]=token
            data=self._get(FILES_URL,params=params).json()
            out.extend(data.get("files",[]));token=data.get("nextPageToken")
            if not token:return out

    def list_folders(self,parent_id):
        return self._list(f"'{parent_id}' in parents and mimeType='{FOLDER_MIME}' and trashed=false")

    def list_images(self,folder_id,query=""):
        q=f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false"
        if query:
            safe=query.replace("\\","\\\\").replace("'","\\'")
            q+=f" and name contains '{safe}'"
        return self._list(q)

    def list_images_recursive(self,folder_id,query=""):
        """Collect images from this folder and all descendant folders, exactly once."""
        results=[];seen_files=set();seen_folders=set()
        def walk(fid):
            if fid in seen_folders:return
            seen_folders.add(fid)
            for image in self.list_images(fid,query):
                if image["id"] not in seen_files:
                    image["_gallery_folder_id"]=fid
                    results.append(image);seen_files.add(image["id"])
            for child in self.list_folders(fid):
                walk(child["id"])
        walk(folder_id)
        return results

    def download_bytes(self,file_id):
        response=self._get(f"{FILES_URL}/{file_id}",params={"alt":"media"},stream=True)
        chunks=[]
        for chunk in response.iter_content(chunk_size=256*1024):
            if chunk:chunks.append(chunk)
        response.close()
        return b"".join(chunks)
