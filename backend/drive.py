import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

READONLY_SCOPE = ["https://www.googleapis.com/auth/drive.readonly"]
FILES_URL = "https://www.googleapis.com/drive/v3/files"

class DriveGallery:
    def __init__(self):
        try:
            info = dict(st.secrets["gdrive_service_account"])
            credentials = service_account.Credentials.from_service_account_info(info, scopes=READONLY_SCOPE)
            self.session = AuthorizedSession(credentials)
            retry = Retry(total=4, connect=4, read=3, status=3, backoff_factor=1,
                          status_forcelist=(429,500,502,503,504),
                          allowed_methods=frozenset(["GET"]), raise_on_status=False)
            adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
            self.session.mount("https://", adapter)
            self.root_id = str(st.secrets["gdrive_root_folder_id"]).strip()
        except Exception as exc:
            raise RuntimeError(f"Could not initialize Google Drive credentials: {exc}") from exc

    def _get(self, url, params=None, stream=False):
        try:
            response = self.session.get(url, params=params, timeout=(15,90), stream=stream)
            if response.status_code >= 400:
                try: detail = response.json().get("error",{}).get("message",response.text)
                except Exception: detail = response.text
                raise RuntimeError(f"Google Drive API HTTP {response.status_code}: {detail}")
            return response
        except requests.exceptions.SSLError as exc:
            raise RuntimeError(f"Google TLS/SSL connection failed after retries: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Google Drive network error: {exc}") from exc

    def _list(self, q):
        result, token = [], None
        while True:
            params = {"q":q,"pageSize":1000,"orderBy":"name",
                      "fields":"nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,webViewLink)",
                      "supportsAllDrives":"true","includeItemsFromAllDrives":"true"}
            if token: params["pageToken"] = token
            data = self._get(FILES_URL, params=params).json()
            result.extend(data.get("files",[]))
            token = data.get("nextPageToken")
            if not token: return result

    def list_folders(self, parent_id):
        q = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        return self._list(q)

    def get_folder(self, folder_id):
        if folder_id == self.root_id: return {"id":self.root_id,"name":"My Private Gallery"}
        data = self._get(f"{FILES_URL}/{folder_id}",params={"fields":"id,name,mimeType"}).json()
        return data if data.get("mimeType") == "application/vnd.google-apps.folder" else None

    def list_images(self, folder_id, query=""):
        q = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false"
        if query:
            safe = query.replace("\\","\\\\").replace("'","\\'")
            q += f" and name contains '{safe}'"
        return self._list(q)

    def download_bytes(self, file_id):
        response = self._get(f"{FILES_URL}/{file_id}",params={"alt":"media"},stream=True)
        chunks=[]
        for chunk in response.iter_content(chunk_size=256*1024):
            if chunk: chunks.append(chunk)
        response.close()
        return b"".join(chunks)
