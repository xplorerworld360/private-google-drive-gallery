# Private Google Drive Streamlit Gallery

A private Streamlit image gallery. Google Drive stores the original images; Streamlit lists albums (Drive folders), previews images, searches filenames, uploads, downloads, creates albums, and deletes images.

## 1. Google Drive setup

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or select an existing project).
3. Enable **Google Drive API** for that project.
4. Create a service account under **IAM & Admin → Service Accounts**.
5. Create a JSON key for the service account and download it securely.
6. Create a root folder in Google Drive, for example `Private Gallery`.
7. Share that root folder with the service account's `client_email` address from the JSON key. Give it **Editor** access so uploads and deletes work.
8. Create album subfolders inside the root folder. Each immediate child folder appears as an album in the app.
9. Copy the root folder ID from its Drive URL:
   `https://drive.google.com/drive/folders/FOLDER_ID`

The app accesses the root folder and its child albums as the service account. The folder must be shared with that service account. Do not make the folder public.

## 2. Install locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.

Paste the service account JSON fields into `[gdrive_service_account]`, set `gdrive_root_folder_id`, and choose a long unique `gallery_password`.

Run:

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit.

## 3. Deploy privately

You can deploy to Streamlit Community Cloud or another host that supports Streamlit. Add the contents of `secrets.toml` in the host's **App settings → Secrets** area. Never commit `secrets.toml`, service-account JSON keys, or passwords to Git.

For a genuinely private deployment, also restrict access at the hosting/network layer (for example, an authenticated company environment, VPN, or identity-aware proxy). The in-app password is an additional gate, not a substitute for host-level access control or per-user identity management.

## 4. Security and behavior

- The service account has access only to folders explicitly shared with it, subject to Google Drive permissions.
- The app uses a single shared gallery password. Anyone who knows it can use the admin actions.
- Upload, download, and delete operate on the actual Google Drive files.
- Deleting an image through Admin deletes it from Drive; this is not just a local removal.
- Albums are immediate subfolders of the configured root folder. Images are listed from the selected album folder; nested subfolders are not recursively scanned.
- The app currently supports common image types and searches by filename.
- For a multi-user production app, replace the shared password with Google OAuth sign-in and per-user authorization, and consider audit logging and upload size limits.

## 5. Troubleshooting

**403 / permission denied:** Confirm Google Drive API is enabled and the root folder is shared with the service account email as Editor.

**Invalid private key:** Preserve the `\\n` line breaks in `private_key` in `secrets.toml`. Copy the value exactly from the downloaded service-account JSON.

**No albums:** Create one or more subfolders directly inside the configured root folder.

**Wrong folder:** Verify the ID in the Drive folder URL, not an image/file URL.

**Large images:** Streamlit must download image bytes to render them. Consider thumbnails or a CDN/object store for very large galleries.
