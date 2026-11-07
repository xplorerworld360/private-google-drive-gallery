# Private Google Drive Gallery — Password Login

This version restores the original password-protected gallery and Google Drive Service Account connection.

## What remains in the app
- Modern dark gallery interface
- Album folders and album filter
- Filename search
- Sort by newest, oldest, name
- Comfortable and compact grid
- Image preview and downloads
- Session-only favourites
- Pagination
- Private password login
- Refresh gallery button

## What is intentionally removed
- Google OAuth sign-in
- In-app Admin Studio
- In-app upload, rename, move and delete actions

Manage your images directly in Google Drive. The gallery reads and displays the images from Drive. Refresh the gallery after making changes in Drive.

## Google Drive setup
1. In Google Cloud Console, create/select a project.
2. Enable Google Drive API.
3. Create a Service Account and generate a JSON key.
4. Create a root folder in your Google Drive, such as `My Private Gallery`.
5. Share that root folder with the Service Account `client_email` and grant **Viewer** access.
6. Create album subfolders inside the root folder and put images inside those folders.
7. Copy the root folder ID from its Drive URL.

The app uses the read-only scope `https://www.googleapis.com/auth/drive.readonly`. It does not need Editor access because all changes are made directly in Drive.

## Streamlit Cloud secrets
Open Manage app → Settings → Secrets and paste the values from `.streamlit/secrets.toml.example`. Set a long unique `gallery_password`. Paste the complete service-account JSON fields into the `[gdrive_service_account]` section.

Never commit `.streamlit/secrets.toml` or the JSON private key to GitHub.

## Requirements and run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Security
The password gate is a simple shared-password layer, not full identity-based authentication. Restrict access to the deployed app where possible. The service account has Viewer access only to the shared root folder. Do not make your Drive folder public.
