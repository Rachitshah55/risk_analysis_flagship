from __future__ import annotations
import os, sys, json, smtplib, ssl, socket, argparse, subprocess
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

# --- Config (env) ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()
SMTP_HOST  = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT  = int(os.getenv("SMTP_PORT", "0") or 0)
SMTP_USER  = os.getenv("SMTP_USER", "").strip()
SMTP_PASS  = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM  = os.getenv("SMTP_FROM", "").strip() or SMTP_USER
ALERT_TO   = [e.strip() for e in os.getenv("ALERT_TO", "").split(",") if e.strip()]
ALERT_MIN_SEVERITY = (os.getenv("ALERT_MIN_SEVERITY") or "warn").lower()
DEFAULT_CHANNEL = (os.getenv("ALERT_CHANNEL") or "both").lower()  # slack|email|both
EMAIL_TRANSPORT = os.getenv("EMAIL_TRANSPORT", "smtp").lower()    # smtp|gmail_api

SEVERITY_ORDER = {"info": 0, "warn": 1, "critical": 2}

def _today_str(date_arg: str | None) -> str:
    return date_arg or datetime.now().strftime("%Y-%m-%d")

def find_alert_files(day: str) -> List[Tuple[str, Path]]:
    out: List[Tuple[str, Path]] = []
    base = ROOT / "docs_global" / "monitoring"
    for sys_name in ("credit", "fraud"):
        d = base / sys_name / day
        p = d / "alert.txt"
        if p.is_file() and p.stat().st_size > 0:
            out.append((sys_name, p))
    return out

def parse_severity(text: str) -> str:
    low = text.lower()
    for lvl in ("critical", "warn", "info"):
        if f"severity:{lvl}" in low:
            return lvl
    if "psi" in low and ("0.25" in low or ">=0.25" in low):
        return "warn"
    return "info"

def should_send(level: str) -> bool:
    return SEVERITY_ORDER.get(level, 1) >= SEVERITY_ORDER.get(ALERT_MIN_SEVERITY, 1)

def post_slack(msg: str) -> bool:
    if not SLACK_WEBHOOK_URL:
        print("[INFO] Slack not configured; printing message\n", msg)
        return False
    try:
        s = requests.Session(); s.trust_env = False
        r = s.post(SLACK_WEBHOOK_URL, json={"text": msg}, timeout=15)
        r.raise_for_status()
        print("[OK] Slack sent.")
        return True
    except Exception as e:
        print("[WARN] Slack send failed:", e)
        return False

# --- Gmail API path (no app passwords) ---
def send_email_via_gmail_api(subject: str, body: str) -> bool:
    try:
        # gmail_api_helper.py must live in the same folder as this file
        from gmail_api_helper import send_gmail_api
    except Exception as e:
        print("[WARN] Gmail API helper not available:", e)
        return False

    to_list = ALERT_TO
    sender = SMTP_FROM or (to_list[0] if to_list else "")
    if not (sender and to_list):
        print("[INFO] Gmail API: missing sender/ALERT_TO; skipping.")
        return False
    try:
        send_gmail_api(subject, body, sender, to_list)
        print("[OK] Gmail API email sent.")
        return True
    except Exception as e:
        print("[WARN] Gmail API send failed:", e)
        return False

# --- SMTP path (fallback/alt transport) ---
def send_email_smtp(subject: str, body: str) -> bool:
    if not (SMTP_HOST and SMTP_PORT and SMTP_FROM and ALERT_TO):
        print("[INFO] SMTP not configured; printing message\n", subject, "\n", body)
        return False

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(ALERT_TO)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if SMTP_PORT == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=15) as s:
                if SMTP_USER and SMTP_PASS:
                    s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                s.ehlo()
                try:
                    s.starttls(context=ssl.create_default_context())
                    s.ehlo()
                except Exception:
                    pass
                if SMTP_USER and SMTP_PASS:
                    s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        print("[OK] Email sent (SMTP).")
        return True
    except Exception as e:
        print("[WARN] Email send failed (SMTP):", e)
        return False

def send_email(subject: str, body: str) -> bool:
    if EMAIL_TRANSPORT == "gmail_api":
        return send_email_via_gmail_api(subject, body)
    # default/fallback
    return send_email_smtp(subject, body)

def format_message(found: List[Tuple[str, Path]], day: str) -> str:
    host = socket.gethostname()
    lines = [f":rotating_light: Risk Alerts for {day} (host {host})"]
    for sys_name, path in found:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        lines.append(f"\n*{sys_name.upper()}* — {path}")
        lines.append("```")
        lines.append(text[:4000])
        lines.append("```")
    lines.append("\nMLflow UI: http://127.0.0.1:5000")
    return "\n".join(lines)

def git_sha_short() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--msg", help="Override message (skips alert.txt scan if provided)")
    ap.add_argument("--subject", help="Email subject override")
    ap.add_argument("--level", default="info", choices=["info","warn","critical"])
    ap.add_argument("--channel", default=DEFAULT_CHANNEL, choices=["slack","email","both"])
    ap.add_argument("--test", action="store_true", help="Send a harmless test")
    args = ap.parse_args()

    if args.test:
        body = f"✅ Test alert — git:{git_sha_short()} — {datetime.now().isoformat(timespec='seconds')}"
        subj = args.subject or "Test Alert (OK)"
        ok = (args.channel in ("slack","both") and post_slack(body)) or False
        ok = (args.channel in ("email","both") and send_email(subj, body)) or ok
        print("[RESULT]", "delivered" if ok else "no-channel-configured")
        sys.exit(0 if ok else 2)

    day = _today_str(args.day)

    if args.msg:
        body = args.msg
        worst = args.level
    else:
        found = find_alert_files(day)
        if not found:
            print(f"[OK] No alert.txt found for {day}.")
            sys.exit(0)
        worst = "info"
        for _, p in found:
            lvl = parse_severity(p.read_text(encoding="utf-8", errors="ignore"))
            if SEVERITY_ORDER.get(lvl, 0) > SEVERITY_ORDER.get(worst, 0):
                worst = lvl
        if not should_send(worst):
            print(f"[INFO] Found alerts at <= '{worst}' but ALERT_MIN_SEVERITY='{ALERT_MIN_SEVERITY}'. Skipping send.")
            sys.exit(0)
        body = format_message(found, day)

    subj = args.subject or f"[RISK ALERT] {day} — worst={worst}"
    ok = False
    if args.channel in ("slack","both"):
        ok = post_slack(body) or ok
    if args.channel in ("email","both"):
        ok = send_email(subj, body) or ok
    print(f"[SENT] {('OK' if ok else 'NOOP')} at level '{worst}'.")
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
