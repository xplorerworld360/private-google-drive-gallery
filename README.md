# Blueglass Gallery — Shared Google Drive + Gmail Access Control

## The intended model

- One owner maintains one central photo/video collection in their Google Drive.
- Every visitor signs in with their own Google account (only `openid`, `email`, `profile` scopes).
- The app checks the signed-in email against an access registry.
- The owner can add Gmail addresses and assign:
  - **Viewer** — view media only.
  - **Downloader** — view and download originals.
  - **Access manager** — view/download and manage Viewer/Downloader grants.
- Only the owner can appoint another Access Manager.
- The Admin page manages people and privileges only. There are no photo upload, rename, delete or folder-management functions.
- All original photos stay in the owner's Google Drive. A server-side Service Account reads the shared gallery, so visitors never connect their personal Drive to this app.

## Google Drive / Service Account setup

1. Create/select a Google Cloud project and enable Google Drive API.
2. Create a Service Account and generate a JSON key.
3. In the owner's Google Drive, create a folder named `Shared Gallery`.
4. Add album folders and images/videos inside it.
5. Share **only the Shared Gallery root folder** with the Service Account email as **Viewer**.
6. Create a separate file in the owner's Drive named `gallery_access.json` with this exact starter content:
   ```json
   {
     "users": {}
   }
   ```
7. Share **only that `gallery_access.json` file** with the Service Account email as **Editor**. Do not grant the service account Editor permission on the gallery folder.
8. Copy the IDs of the Shared Gallery folder and `gallery_access.json` file from their Drive URLs.

Resulting permissions:
- Shared Gallery folder → Service Account: Viewer.
- gallery_access.json file → Service Account: Editor.
- Visitors → no direct access to the owner's Drive. They only view content through the authenticated app.

## Google OAuth setup (visitor sign-in)

1. In Google Cloud Console, open Google Auth Platform.
2. Configure the app name, support email and developer contact.
3. Choose **External** for regular Gmail accounts.
4. Add `openid`, `email`, `profile` as the app's only end-user OAuth scopes.
5. Create an OAuth Client ID of type **Web application**.
6. Add the exact Streamlit app URL as an Authorized redirect URI, e.g. `https://your-app.streamlit.app`.
7. Copy the OAuth Client ID and Client Secret.

This app does **not** request a Google Drive scope from visitors. Drive is accessed server-side by the Service Account. The Google sign-in identifies the visitor; the allow-list decides if they may view or download.

For an External OAuth app left in Testing mode, add each permitted visitor as a test user in Google Auth Platform. For broad access, publish the consent screen to Production. Basic identity scopes are used here; do not add Drive scopes to the visitor OAuth client.

## Streamlit Cloud Secrets

Paste all values in Manage app → Settings → Secrets:

```toml
[google_oauth]
client_id = "YOUR_GOOGLE_OAUTH_CLIENT_ID"
client_secret = "YOUR_GOOGLE_OAUTH_CLIENT_SECRET"
redirect_uri = "https://your-app.streamlit.app"

[gallery]
owner_email = "owner@gmail.com"
root_folder_id = "SHARED_GALLERY_FOLDER_ID"
access_registry_file_id = "GALLERY_ACCESS_JSON_FILE_ID"

[gdrive_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY
-----END PRIVATE KEY-----
"""
client_email = "YOUR_SERVICE_ACCOUNT_EMAIL"
client_id = "YOUR_SERVICE_ACCOUNT_CLIENT_ID"
token_uri = "https://oauth2.googleapis.com/token"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_SERVICE_ACCOUNT_CERT_URL"
universe_domain = "googleapis.com"
```

The Service Account must have Viewer access to the gallery folder and Editor access to the access registry JSON file. The app cannot persist access changes without Editor access to that one registry file.

## Deployment

1. Push this project to GitHub.
2. Select `app.py` as the Streamlit entry point.
3. Add the Secrets above.
4. Reboot the app.
5. Sign in as the owner account first.
6. Open Access Management and add visitor Gmail addresses.

## Access roles

- Viewer: can browse gallery media, cannot download originals.
- Downloader: can browse and download originals.
- Access manager: can browse/download and manage Viewer/Downloader access. Cannot grant Access Manager.
- Owner: fixed by `gallery.owner_email`, cannot be revoked or removed.

Revocation disables access immediately on the next authorization check (registry cached for 30 seconds per browser session). Removing a user record permanently removes that email from the registry.

## Design and performance

- Blue/white glass appearance with a Light/Dark switch.
- Responsive photo/video grid, album navigation, breadcrumbs, search, sorting, media filters and favourites.
- Full-resolution media fetched only when previewed or downloaded.
- Recursive Drive metadata index cached for 10 minutes and thumbnails cached for 30 minutes.
- Sibling folder requests run concurrently.

## Security notes

The web app's Service Account is a server-side principal. Share only the gallery folder as Viewer and only the ACL JSON file as Editor. Do not share the owner's entire Drive. Do not commit Streamlit Secrets, Service Account keys, OAuth client secrets or the ACL file contents to GitHub.

The app restricts gallery results to the configured root and checks user roles before rendering the Gallery or Access Management pages. This is application-level access control, not a formal guarantee against vulnerabilities in the app or Streamlit hosting. Keep the repository private and deploy only trusted code.

OAuth tokens are used only to identify the user and are not saved as Drive credentials. Streamlit session state holds the verified identity until logout or session expiry.
