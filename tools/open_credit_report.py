from pathlib import Path
from datetime import date
import argparse, webbrowser, sys

ROOT = Path(r"C:\DevProjects\risk_analysis_flagship")
BASE = ROOT / "docs_global" / "reports" / "credit"

def open_today():
    d = date.today().strftime("%Y-%m-%d")
    path = BASE / d / "credit_daily_report.html"
    if path.exists():
        webbrowser.open_new_tab(path.as_uri())
        print(f"[Open] {path}")
        return 0
    print(f"[Open] Report not found: {path}", file=sys.stderr)
    return 1

def open_latest():
    if not BASE.exists():
        print(f"[Open] Base folder not found: {BASE}", file=sys.stderr)
        return 1
    dirs = sorted([p for p in BASE.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
    if not dirs:
        print(f"[Open] No report folders under {BASE}", file=sys.stderr)
        return 1
    path = dirs[0] / "credit_daily_report.html"
    if path.exists():
        webbrowser.open_new_tab(path.as_uri())
        print(f"[Open] {path}")
        return 0
    print(f"[Open] Report not found: {path}", file=sys.stderr)
    return 1

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--latest", action="store_true", help="Open the most recent report instead of today's")
    args = ap.parse_args()
    rc = open_latest() if args.latest else open_today()
    sys.exit(rc)
