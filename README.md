# Apple-inspired Private Google Drive Photos

## Design and behaviour
- Clean Apple Photos-inspired light interface.
- Sidebar for All Photos and top-level albums.
- Root All Photos view recursively collects images from every nested folder.
- Album selection opens that folder and includes images from its descendant folders.
- Folder tiles are shown separately from photo tiles; folders are never mixed into image results.
- Responsive square thumbnail grid, 5 columns on desktop and fewer on smaller screens.
- Click a photo to open a clean full-screen viewer.
- Swipe left/right, keyboard arrows, close with Escape, and download original.
- Filename search, newest/oldest/name sorting, density selector and pagination.
- Password login; no Google OAuth sign-in.
- Google Drive is read-only; manage files directly in Drive.

## Root-folder behaviour
The root view is intentionally named **All Photos**. It lists all image files recursively from the root and every nested album folder. The Albums section separately lists only direct child folders. Selecting an album filters the recursive image list to that album and its descendants. This avoids showing folder entries as if they were photos.

## Google Drive setup
Enable Drive API, create a service account, share the root folder with its `client_email` as Viewer, and place images in folders below the root.

## Streamlit Secrets
Keep `gallery_password`, `gdrive_root_folder_id`, and `[gdrive_service_account]` exactly as configured in your existing deployment. Do not commit the actual secrets file or private key to GitHub.

## Deployment
Replace the app files with this project, keep `runtime.txt`, push to GitHub and reboot Streamlit Cloud.
