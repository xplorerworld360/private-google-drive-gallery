<<<<<<< HEAD
import requests
=======
>>>>>>> parent of 46b59fa (ssl)
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io

<<<<<<< HEAD
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
=======
READONLY_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]

class DriveGallery:
    def __init__(self):
        try:
            info = dict(st.secrets["gdrive_service_account"])
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=READONLY_SCOPE
            )
            self.api = build("drive", "v3", credentials=credentials, cache_discovery=False)
            self.root_id = str(st.secrets["gdrive_root_folder_id"])
        except Exception as exc:
            raise RuntimeError(f"Google Drive credentials are not configured correctly: {exc}") from exc

    def _list(self, query):
        output, token = [], None
        try:
            while True:
                result = self.api.files().list(
                    q=query,
                    pageSize=1000,
                    pageToken=token,
                    orderBy="name",
                    fields="nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,webViewLink)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                ).execute()
                output.extend(result.get("files", []))
                token = result.get("nextPageToken")
                if not token:
                    return output
        except HttpError as exc:
            raise RuntimeError(f"Google Drive API error: {exc}") from exc
>>>>>>> parent of 46b59fa (ssl)

    def list_folders(self,parent_id):
        return self._list(f"'{parent_id}' in parents and mimeType='{FOLDER_MIME}' and trashed=false")

<<<<<<< HEAD
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
=======
    def list_images(self, album_id=None, query=""):
        parents = [album_id] if album_id else [a["id"] for a in self.list_albums()]
        images = []
        for parent in parents:
            q = f"'{parent}' in parents and mimeType contains 'image/' and trashed=false"
            if query:
                safe_query = query.replace("\\", "\\\\").replace("'", "\\'")
                q += f" and name contains '{safe_query}'"
            images.extend(self._list(q))
        return sorted(images, key=lambda x: x.get("name", "").lower())

    def download_bytes(self, file_id):
        try:
            request = self.api.files().get_media(fileId=file_id, supportsAllDrives=True)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except HttpError as exc:
            raise RuntimeError(f"Could not download image: {exc}") from exc
>>>>>>> parent of 46b59fa (ssl)
