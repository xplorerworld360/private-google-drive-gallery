# Modern Streamlit Google Drive Gallery

This version uses **Google OAuth as your own Google account**, not a service account. It includes a modern gallery and a separate Admin Studio.

## Google setup
1. Create/select a project at https://console.cloud.google.com/
2. Enable Google Drive API.
3. Open Google Auth Platform / OAuth consent screen. Configure app name and support email. For personal Gmail choose External, and add your account as a test user while in Testing.
4. Create OAuth Client ID → Web application.
5. Add exact authorized redirect URI, e.g. `https://your-app.streamlit.app`. For local testing also add `http://localhost:8501`.
6. Copy Client ID and Client Secret.

## Streamlit secrets
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` locally, or paste into Streamlit Cloud → Manage app → Settings → Secrets:

```toml
[google_oauth]
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"
redirect_uri = "https://your-app.streamlit.app"
root_folder_id = "YOUR_DRIVE_ROOT_FOLDER_ID"
```

Create a root folder in your own Drive, create album subfolders inside it, and copy the root folder ID from its Drive URL. No sharing with a service account is required.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

Deploy the GitHub repository with `app.py` as the entry point and add the same secrets in Streamlit Cloud. Never commit secrets.

## Notes
- OAuth asks for the broad `https://www.googleapis.com/auth/drive` scope because the app lists, uploads, renames and deletes Drive files.
- This starter keeps OAuth tokens in Streamlit session state. A new browser session or server restart may require signing in again. For durable production login, store refresh tokens encrypted in a secure database.
- Google OAuth apps left in Testing can have refresh tokens expire after seven days for non-basic scopes. For longer-term use, configure Production status and meet any Google verification requirements.
- This is a single-owner gallery. Restrict access to the Streamlit app itself; anyone able to use the connected app session can manage the owner's selected Drive folder.
