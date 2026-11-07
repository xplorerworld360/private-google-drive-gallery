# Private Google Drive Gallery — Swipe Viewer + Password Login

## What this version includes
- Original password-only login (no Google OAuth sign-in)
- Read-only Service Account connection to Google Drive
- Clean, compact gallery interface
- Album selection, filename search and sorting
- Swipe left/right on touch devices
- Previous/next arrows and keyboard arrow navigation
- Click image to open immersive viewer
- Thumbnail strip for direct image selection
- Download original image from viewer
- Favourites toggle within the current viewer session
- Page through larger collections
- Manage files and folders directly in Google Drive

## Fix for SSL RECORD_LAYER_FAILURE
This version replaces the Google API client's older httplib2 transport with Google's `AuthorizedSession` using Requests. It includes HTTPS retries, explicit timeouts and certifi CA certificates. `runtime.txt` requests Python 3.12.10 instead of the Python 3.14 runtime shown in the deployment logs.

Do not disable SSL certificate verification.

## Google Drive configuration
1. Enable Google Drive API in your Google Cloud project.
2. Create a Service Account and download a JSON key.
3. Create a root folder in Google Drive.
4. Share that folder with the service-account `client_email` using Viewer permission.
5. Create album subfolders directly inside the root folder.
6. Add `gallery_password`, `gdrive_root_folder_id`, and all fields from the service-account JSON under `[gdrive_service_account]` in Streamlit Cloud → Manage app → Settings → Secrets.
7. Do not upload `secrets.toml` or the JSON private key to GitHub.

The code uses `https://www.googleapis.com/auth/drive.readonly`; all upload, rename and delete operations are performed manually in Google Drive.

## Deploy
Push all files to GitHub, including `runtime.txt`. Keep `.streamlit/secrets.toml` out of Git. Reboot the Streamlit app so the new runtime and dependencies are installed.

## Troubleshooting
- If SSL errors persist after this transport change and Python 3.12 runtime, inspect the latest Streamlit Cloud logs. Do not turn off TLS verification.
- A 403 error generally means the Drive folder is not shared with the service account, the API is disabled, or the account lacks access.
- An empty gallery can mean the root folder ID is wrong or album folders are not direct children of the root folder.
