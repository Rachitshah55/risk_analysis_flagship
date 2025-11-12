#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alert Bridge — Slack + Email (Gmail API or SMTP)
- Loads .env from repo root (no extra deps), with backward-compat to your existing keys.
- Keeps Gmail API path intact; Slack is additive via SLACK_WEBHOOK_URL.
- Severity threshold via ALERT_MIN_SEVERITY (info < warn < error).
- CLI:
    python alert_bridge.py --print-config
    python alert_bridge.py --test
    python alert_bridge.py --title "X" --body "Y" --severity warn
    python alert_bridge.py --slack-only
    python alert_bridge.py --email-only
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
from typing import Optional

# ---------- Path helpers ----------
HERE = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ENV_PATH = os.path.join(REPO_ROOT, ".env")

SECRETS_DIR = os.path.join(HERE, "secrets")
DEFAULT_CREDS = os.path.join(SECRETS_DIR, "credentials.json")
DEFAULT_TOKEN = os.path.join(SECRETS_DIR, "token.json")

# ---------- Minimal .env loader (no dependencies) ----------
def load_env_file(path: str) -> None:
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # don't clobber already-existing env
                os.environ.setdefault(k, v)
    except Exception as e:
        print(f"[WARN] Could not read .env: {e}", file=sys.stderr)

def apply_compat_env_aliases() -> None:
    """
    Map your old keys to the new ones if the new ones are missing.
    - ALERT_TO -> ALERT_TO_EMAIL
    - SMTP_FROM -> ALERT_FROM_EMAIL
    - GMAIL_CLIENT_SECRET_JSON -> GMAIL_CREDENTIALS_JSON
    """
    alias_pairs = [
        ("ALERT_TO_EMAIL", "ALERT_TO"),
        ("ALERT_FROM_EMAIL", "SMTP_FROM"),
        ("GMAIL_CREDENTIALS_JSON", "GMAIL_CLIENT_SECRET_JSON"),
    ]
    for new_key, old_key in alias_pairs:
        if not os.environ.get(new_key) and os.environ.get(old_key):
            os.environ[new_key] = os.environ[old_key]

# load .env first, then apply aliases
load_env_file(ENV_PATH)
apply_compat_env_aliases()

# ---------- Severity handling ----------
_SEV_ORDER = {"info": 0, "warn": 1, "warning": 1, "error": 2}
def _sev_value(name: str) -> int:
    return _SEV_ORDER.get(str(name).lower().strip(), 0)
def _meets_threshold(sev: str, min_sev_env: Optional[str]) -> bool:
    min_name = (min_sev_env or "info").lower().strip()
    return _sev_value(sev) >= _sev_value(min_name)

# ---------- Slack ----------
def send_slack(title: str, body: str, severity: str = "info") -> bool:
    url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        return False
    payload = {"text": f"*{severity.upper()}* — {title}\n{body}"}
    try:
        try:
            import requests  # prefer requests if present
            r = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=10)
            ok = r.status_code in (200, 204)
            if ok:
                print("[OK] Slack message delivered.")
            else:
                print(f"[WARN] Slack returned HTTP {r.status_code}: {r.text}", file=sys.stderr)
            return ok
        except Exception:
            # fallback to stdlib
            import urllib.request
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = 200 <= resp.status < 300
                if ok:
                    print("[OK] Slack message delivered.")
                else:
                    print(f"[WARN] Slack returned HTTP {resp.status}", file=sys.stderr)
                return ok
    except Exception as e:
        print(f"[ERR] Slack send failed: {e}", file=sys.stderr)
        return False

# ---------- Gmail API (Installed App) ----------
_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def _load_gmail_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except Exception as e:
        print(f"[WARN] Gmail API libs not installed: {e}", file=sys.stderr)
        return None

    cred_path = os.getenv("GMAIL_CREDENTIALS_JSON", DEFAULT_CREDS)
    token_path = os.getenv("GMAIL_TOKEN_JSON", DEFAULT_TOKEN)

    creds = None
    if os.path.isfile(token_path):
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(token_path, _SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            if not os.path.isfile(cred_path):
                print(f"[ERR] Missing Gmail credentials.json at: {cred_path}", file=sys.stderr)
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(cred_path, _SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"[ERR] Gmail OAuth failed: {e}", file=sys.stderr)
                return None
        try:
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        except Exception:
            pass

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        print(f"[ERR] Gmail service build failed: {e}", file=sys.stderr)
        return None

def send_gmail_api(subject: str, body_text: str, to_email: str) -> bool:
    service = _load_gmail_service()
    if service is None:
        return False
    from email.mime.text import MIMEText
    msg = MIMEText(body_text, _subtype="plain", _charset="utf-8")
    msg["to"] = to_email
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        print("[OK] Gmail API email sent.")
        return True
    except Exception as e:
        print(f"[ERR] Gmail API send failed: {e}", file=sys.stderr)
        return False

# ---------- SMTP (optional) ----------
def send_smtp(subject: str, body_text: str, to_email: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    use_tls = os.getenv("SMTP_TLS", "true").lower().strip() != "false"
    from_email = os.getenv("ALERT_FROM_EMAIL", user or to_email)

    if not (host and to_email):
        print("[WARN] SMTP not configured; skipping SMTP", file=sys.stderr)
        return False

    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body_text, _subtype="plain", _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        if use_tls and port != 465:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                if user and password:
                    server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
        print("[OK] SMTP email sent.")
        return True
    except Exception as e:
        print(f"[ERR] SMTP send failed: {e}", file=sys.stderr)
        return False

# ---------- Bridge ----------
def send_alert(title: str, body: str, severity: str = "info",
               email_only: bool = False, slack_only: bool = False) -> bool:
    min_sev = os.getenv("ALERT_MIN_SEVERITY", "info")
    if not _meets_threshold(severity, min_sev):
        print(f"[SKIP] severity '{severity}' below threshold '{min_sev}'.")
        return True

    delivered_any = False

    if not email_only:
        ok_slack = send_slack(title, body, severity)
        delivered_any = delivered_any or ok_slack

    if not slack_only:
        transport = os.getenv("EMAIL_TRANSPORT", "gmail_api").strip().lower()
        to_email = os.getenv("ALERT_TO_EMAIL", "").strip()
        if not to_email and transport != "disabled":
            print("[WARN] ALERT_TO_EMAIL not set; skipping email channel", file=sys.stderr)
        else:
            subject = f"[{severity.upper()}] {title}"
            ok_mail = False
            if transport == "gmail_api":
                ok_mail = send_gmail_api(subject, body, to_email)
            elif transport == "smtp":
                ok_mail = send_smtp(subject, body, to_email)
            delivered_any = delivered_any or ok_mail

    return delivered_any

# ---------- CLI ----------
def _build_parser():
    p = argparse.ArgumentParser(description="Alert Bridge (Slack + Email)")
    p.add_argument("--test", action="store_true", help="Send a test message to all configured channels.")
    p.add_argument("--title", default=None, help="Alert title/subject.")
    p.add_argument("--body", default=None, help="Alert body text.")
    p.add_argument("--severity", default="info", choices=["info","warn","warning","error"], help="Severity level.")
    p.add_argument("--slack-only", action="store_true", help="Send only to Slack.")
    p.add_argument("--email-only", action="store_true", help="Send only to Email.")
    p.add_argument("--print-config", action="store_true", help="Print resolved config (redacts secrets).")
    return p

def _print_config():
    def redact(v: Optional[str]) -> str:
        if not v:
            return ""
        if len(v) <= 8:
            return "*" * len(v)
        return v[:4] + "..." + v[-4:]

    cfg = {
        "ENV_PATH_LOADED": os.path.isfile(ENV_PATH),
        "ALERT_MIN_SEVERITY": os.getenv("ALERT_MIN_SEVERITY", "info"),
        "EMAIL_TRANSPORT": os.getenv("EMAIL_TRANSPORT", "gmail_api"),
        "ALERT_TO_EMAIL": os.getenv("ALERT_TO_EMAIL", ""),
        "ALERT_FROM_EMAIL": os.getenv("ALERT_FROM_EMAIL", ""),
        "SLACK_WEBHOOK_URL": redact(os.getenv("SLACK_WEBHOOK_URL", "")),
        "GMAIL_CREDENTIALS_JSON": os.getenv("GMAIL_CREDENTIALS_JSON", DEFAULT_CREDS),
        "GMAIL_TOKEN_JSON": os.getenv("GMAIL_TOKEN_JSON", DEFAULT_TOKEN),
        "SMTP_HOST": os.getenv("SMTP_HOST", ""),
        "SMTP_PORT": os.getenv("SMTP_PORT", ""),
        "SMTP_USER": os.getenv("SMTP_USER", ""),
        "SMTP_PASS": redact(os.getenv("SMTP_PASS", "")),
        "SMTP_TLS": os.getenv("SMTP_TLS", "true"),
    }
    print(json.dumps(cfg, indent=2))

def main():
    parser = _build_parser()
    args = parser.parse_args()

    # honor print-config and EXIT (no implicit send)
    if args.print_config:
        _print_config()
        return 0

    # normalize severity once and reuse
    sev = "warning" if args.severity in ("warn", "warning") else args.severity

    # test path should HONOR --severity (not hard-code info)
    if args.test:
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = "Alert Bridge — Test"
        body = f"This is a test alert at {now}\nProject: risk_analysis_flagship"
        ok = send_alert(title, body, severity=sev,
                        email_only=args.email_only, slack_only=args.slack_only)
        print("[RESULT] delivered" if ok else "[RESULT] failed")
        return 0 if ok else 2

    # normal mode
    title = args.title or f"Alert at {dt.datetime.now().isoformat(timespec='seconds')}"
    body  = args.body  or "(no body)"

    ok = send_alert(title, body, severity=sev,
                    email_only=args.email_only, slack_only=args.slack_only)  # <- underscore
    print("[RESULT] delivered" if ok else "[RESULT] failed")
    return 0 if ok else 2

if __name__ == "__main__":
    sys.exit(main())
