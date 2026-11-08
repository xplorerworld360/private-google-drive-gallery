# Google Drive Gallery — Google Sign-In + Admin Studio

A Streamlit photo/video gallery with account-specific Google Drive access, a separate admin page, fast metadata indexing, cached thumbnails, and Light/Dark appearance modes.

## Features

### Gallery
- Google sign-in; no shared gallery password.
- Each signed-in account gets a personal gallery folder named **My Streamlit Gallery** in its own My Drive.
- Optional migration to an existing gallery root folder, but only when the signed-in account owns it.
- Responsive thumbnail grid; comfortable/dense layout.
- Root view recursively includes media in nested folders.
- Album navigation, breadcrumb context, filename search and sorting.
- Photo/video filters, session favourites and pagination.
- Full-size viewer with previous/next navigation and original download.
- Light and Dark theme switch.

### Admin Studio
- Upload multiple images/videos to a selected album.
- Create nested albums/folders.
- Search and filter media.
- Rename files and folders.
- Move media between albums.
- Move files to Google Drive Trash (recoverable), with confirmation.
- Bulk move selected media to Trash.
- Delete empty albums only; folders containing files must be emptied first.
- Account page shows which Google account is connected.

### Account isolation
The app creates or reuses a root folder owned by the signed-in Google account. Admin actions validate that a file or folder is inside this account's gallery root and is owned by that user. The app does not list or manage another account's gallery.

The OAuth token itself requests the broad Drive `drive` scope because the app needs to list existing files and create, upload, move, rename and trash files. Google describes this scope as permission to see, edit, create and delete all Drive files. The app's code limits its own Admin actions to the user's gallery root, but the underlying token is broader. Keep the application code private/trusted and review Google's verification requirements before public distribution.

## Google Cloud setup

### 1. Create a project and enable Drive API
1. Open https://console.cloud.google.com/
2. Create a project or select an existing one.
3. Enable **Google Drive API**: https://console.cloud.google.com/apis/library/drive.googleapis.com

### 2. Configure OAuth consent
1. Open Google Auth Platform: https://console.cloud.google.com/auth/overview
2. Configure app name, support email and developer contact email.
3. Choose **External** for personal Gmail accounts.
4. Add your Gmail address as a **Test user** while the app is in Testing.
5. Under Data Access, add:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/drive`

### 3. Create OAuth Client ID
1. Open https://console.cloud.google.com/auth/clients
2. Click Create Client.
3. Application type: **Web application**.
4. Add the exact deployed URL as an Authorized redirect URI. Example:
   `https://app-app-drive-gallery-gokul.streamlit.app`
5. For local development also add:
   `http://localhost:8501`
6. Copy the Client ID and Client Secret.

The redirect URI must exactly match the Streamlit Secrets value (scheme, hostname, case and trailing slash).

### 4. Configure Streamlit Cloud Secrets
Open the app in Streamlit Community Cloud → **Manage app → Settings → Secrets** and paste:

```toml
[google_oauth]
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
redirect_uri = "https://app-app-drive-gallery-gokul.streamlit.app"

# Optional migration: reuse an existing gallery folder only if the signed-in account owns it.
# legacy_gallery_folder_id = "YOUR_OLD_GALLERY_FOLDER_ID"
```

For a legacy folder ID, put `legacy_gallery_folder_id` at the top level (before `[google_oauth]`):

```toml
legacy_gallery_folder_id = "YOUR_OLD_GALLERY_FOLDER_ID"

[google_oauth]
client_id = "..."
client_secret = "..."
redirect_uri = "https://app-app-drive-gallery-gokul.streamlit.app"
```

If you omit `legacy_gallery_folder_id`, the app also checks the old top-level `gdrive_root_folder_id` secret used by the Service Account version. It reuses that folder only if the currently signed-in Google account owns it. Otherwise, each user gets a new `My Streamlit Gallery` folder in their own My Drive. Put any legacy ID above the `[google_oauth]` table in TOML; values after that header belong to the OAuth section.

**Remove old Service Account secrets** (`gdrive_service_account`) from Streamlit Cloud after moving to this OAuth version. The new version does not use a Service Account or `gallery_password`.

### 5. Deploy
1. Commit the project files to GitHub.
2. Set Streamlit's entry point to `app.py`.
3. Add the Secrets above.
4. Reboot the Streamlit app.
5. Sign in with Google and grant Drive access.
6. Open **Admin Studio** to upload images and create albums.

## Local development

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Use `http://localhost:8501` as the local `redirect_uri` and register it in the OAuth client.

## Performance design
- One recursive Drive metadata index per Streamlit user session, cached for 10 minutes.
- Folder traversal scans sibling folders concurrently.
- Thumbnail bytes are cached per session and keyed by file ID + Drive thumbnail version/modified time.
- Full-resolution bytes are fetched only when the user opens or downloads a media item.
- Admin mutations invalidate the metadata and thumbnail caches.

The first visit after login or a manual refresh must build the folder index. Subsequent gallery reruns, filtering and navigation reuse it.

## OAuth and deployment notes
- Google OAuth uses an authorization-code flow, signed `state`, OpenID Connect nonce validation, account selection, offline access and token refresh.
- This starter stores tokens in Streamlit session state, not a persistent token database. A new browser session or a server-side session reset may require signing in again.
- OAuth apps left in Testing can have authorizations and refresh tokens expire after seven days when requesting Drive scopes. For ongoing use, move the consent screen to Production and satisfy Google's verification requirements that apply to the Drive scope.
- Do not commit `.streamlit/secrets.toml`, client secrets, access tokens or refresh tokens to GitHub.
- A public Streamlit URL lets visitors reach the sign-in page. Only Google accounts allowed by your OAuth consent configuration can authorize the app.
