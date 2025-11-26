from __future__ import annotations
import os, base64
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

ROOT = Path(__file__).resolve().parents[2]
CLIENT_SECRET = Path(os.getenv("GMAIL_CLIENT_SECRET_JSON", ROOT / "shared_env" / "secrets" / "client_secret_gmail.json"))
TOKEN_JSON    = Path(os.getenv("GMAIL_TOKEN_JSON", ROOT / "shared_env" / "secrets" / "gmail_token.json"))

def _get_service():
    creds = None
    if TOKEN_JSON.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_JSON), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            # Opens a local browser once on first run; stores refresh token afterwards.
            creds = flow.run_local_server(port=0)
        TOKEN_JSON.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_JSON.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)

def send_gmail_api(subject: str, body: str, sender: str, recipients: list[str]) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Date"] = formatdate(localtime=True)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    svc = _get_service()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()

if __name__ == "__main__":
    # One-time helper to create or refresh gmail_token.json locally
    _get_service()
    print(f"Gmail token stored at: {TOKEN_JSON}")
