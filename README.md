# Private Gallery — Responsive Grid + Folder Navigation

- Password-only login; no Google OAuth sign-in.
- Read-only Google Drive service-account access.
- Responsive grid: 4–8 columns depending on selected density and screen size.
- Displays many images together instead of a single large carousel.
- Nested folder navigation up to four levels, with folder tiles and breadcrumb.
- Search filenames within the currently selected folder.
- Sort by newest, oldest or filename.
- Click any thumbnail for a full-screen viewer.
- Swipe left/right in the viewer, keyboard arrow navigation, download original.
- Pagination (48 images per page) for performance.
- Manage all files and folders directly in Google Drive.

## Google Drive
Enable Drive API, create a service account, share the root folder with the service-account email as Viewer, and create album/subfolder hierarchy below the root folder.

## Streamlit Secrets
Keep the existing values:
- `gallery_password`
- `gdrive_root_folder_id`
- `[gdrive_service_account]` with the service-account JSON fields.

Do not commit actual secrets or the private key to GitHub.

## Deployment
Push the project files including `runtime.txt`. Reboot the Streamlit app. The Drive connector uses Requests-based AuthorizedSession, certifi, timeouts and retries; TLS certificate verification remains enabled.
