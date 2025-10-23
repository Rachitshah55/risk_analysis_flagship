# shared_env/monitoring/alert_bridge.py
from __future__ import annotations
import os, sys, json, smtplib, ssl, socket
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]  # repo root
load_dotenv(ROOT / ".env")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "0") or 0)
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
ALERT_TO = os.getenv("ALERT_TO", "").strip()
ALERT_MIN_SEVERITY = (os.getenv("ALERT_MIN_SEVERITY") or "warn").lower()

SEVERITY_ORDER = {"info": 0, "warn": 1, "critical": 2}

def _today_str(date_arg: str | None) -> str:
    if date_arg:
        return date_arg
    # Run on local time (PT). Task Scheduler will invoke daily.
    return datetime.now().strftime("%Y-%m-%d")

def find_alert_files(day: str) -> List[Tuple[str, Path]]:
    candidates = []
    # Credit monitor
    cdir = ROOT / "docs_global" / "monitoring" / "credit" / day
    # Fraud monitor
    fdir = ROOT / "docs_global" / "monitoring" / "fraud" / day
    for sys_name, d in [("credit", cdir), ("fraud", fdir)]:
        if d.is_dir():
            alert = d / "alert.txt"
            if alert.exists() and alert.stat().st_size > 0:
                candidates.append((sys_name, alert))
    return candidates

def parse_severity(text: str) -> str:
    # very light parsing: look for severity: <level>
    for lvl in ("critical", "warn", "info"):
        if f"severity:{lvl}" in text.lower():
            return lvl
    # fallback: detect phrases
    if "psi" in text.lower() and ("0.25" in text or ">=0.25" in text.lower()):
        return "warn"
    return "info"

def should_send(level: str) -> bool:
    return SEVERITY_ORDER.get(level, 1) >= SEVERITY_ORDER.get(ALERT_MIN_SEVERITY, 1)

def _slack(msg: str) -> None:
    if not SLACK_WEBHOOK_URL:
        print("[INFO] Slack not configured; printing message\n", msg)
        return
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json={"text": msg}, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print("[WARN] Slack send failed:", e)

def _email(subject: str, body: str) -> None:
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and ALERT_TO):
        print("[INFO] SMTP not configured; printing message\n", subject, "\n", body)
        return
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as s:
            s.login(SMTP_USER, SMTP_PASS)
            m = EmailMessage()
            m["From"] = SMTP_USER
            m["To"] = ALERT_TO
            m["Subject"] = subject
            m.set_content(body)
            s.send_message(m)
    except Exception as e:
        print("[WARN] Email send failed:", e)

def format_message(found: List[Tuple[str, Path]], day: str) -> str:
    host = socket.gethostname()
    lines = [f":rotating_light: Risk Alerts for {day} (host {host})"]
    for sys_name, path in found:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        lines.append(f"\n*{sys_name.upper()}* — {path}")
        lines.append("```")
        lines.append(text[:4000])  # keep messages short-ish
        lines.append("```")
    # Link to MLflow UI (local)
    lines.append("\nMLflow UI: http://127.0.0.1:5000")
    return "\n".join(lines)

def main(day: str | None = None):
    day = _today_str(day)
    found = find_alert_files(day)
    if not found:
        print(f"[OK] No alert.txt found for {day}.")
        return 0
    # Compute worst severity
    worst = "info"
    for _, p in found:
        lvl = parse_severity(p.read_text(encoding="utf-8", errors="ignore"))
        if SEVERITY_ORDER.get(lvl, 0) > SEVERITY_ORDER.get(worst, 0):
            worst = lvl
    if not should_send(worst):
        print(f"[INFO] Found alerts at <= '{worst}' but ALERT_MIN_SEVERITY='{ALERT_MIN_SEVERITY}'. Skipping send.")
        return 0
    msg = format_message(found, day)
    _slack(msg)
    _email(f"[RISK ALERT] {day} — worst={worst}", msg)
    print(f"[SENT] Alerts delivered at level '{worst}' for {len(found)} system(s).")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
