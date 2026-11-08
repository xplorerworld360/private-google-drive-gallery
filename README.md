# Optimized Private Google Drive Gallery

## Performance changes
- Builds one recursive gallery metadata index in parallel (10 folder workers) and caches it for 10 minutes.
- Folder navigation and filename search are local filters after the first index build.
- Caches Drive thumbnails in a bounded in-process cache.
- Uses Drive `thumbnailLink` instead of downloading full image originals for grid previews. Google documents that thumbnail links are short-lived and private files require credentialed requests.
- Fetches thumbnails concurrently (10 workers).
- Downloads full-resolution content only after opening a photo.
- Pages 60 items at a time.
- Uses lightweight fields for metadata listing and only loads current folder hierarchy.
- Refresh library clears Streamlit's metadata and thumbnail caches.

## UI/features
- Apple-inspired light interface.
- Root All Photos recursively collects images from nested folders.
- Sidebar album navigation, folder cards and breadcrumbs.
- Search by filename across current album or all photos.
- Sort newest/oldest/name.
- Comfortable/dense responsive grid.
- Session favourites.
- Full-resolution modal viewer with download and previous/next controls.
- Password login; no Google OAuth sign-in.
- Read-only Drive access; file management is done directly in Google Drive.

## Drive setup
Keep your existing Streamlit Secrets:
- `gallery_password`
- `gdrive_root_folder_id`
- `[gdrive_service_account]` with your service-account JSON fields.

Share the root folder with the Service Account email as Viewer. Do not commit secrets or private keys to GitHub.

## Deploy
Replace the project files with this archive's files, include `runtime.txt`, push to GitHub and reboot Streamlit Cloud.

## Notes
Google Drive API's `thumbnailLink` is short-lived and private thumbnails must be fetched with credentials. This application caches downloaded thumbnail bytes for 20 minutes and metadata for 10 minutes; use Refresh library to invalidate caches after Drive changes. Sources: https://developers.google.com/workspace/drive/api/guides/file-metadata
