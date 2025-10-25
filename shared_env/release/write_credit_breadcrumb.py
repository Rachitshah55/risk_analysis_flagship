from pathlib import Path
from datetime import datetime
import argparse, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / "docs_global" / "releases"

def git_sha_short() -> str:
    try:
        r = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--model", required=False, help="Model dir (relative to repo)")
    ap.add_argument("--report", required=False, help="Report path (relative to repo)")
    ap.add_argument("--operator", default="Rachit")
    ap.add_argument("--notes", default="Promoted after KPI review.")
    args = ap.parse_args()

    day = args.date or datetime.now().strftime("%Y-%m-%d")
    REL.mkdir(parents=True, exist_ok=True)
    out = REL / f"credit_PROD_{day}.txt"

    model = args.model or "credit_scoring_system/models/<fill_model_dir>"
    report = args.report or f"docs_global/reports/credit/{day}/credit_daily_report.html"
    commit = git_sha_short()

    body = "\n".join([
        f"Model: {model}",
        f"Report: {report}",
        f"Commit: {commit}",
        f"Operator: {args.operator}",
        f"Notes: {args.notes}",
    ]) + "\n"

    out.write_text(body, encoding="utf-8")
    print(f"[OK] Wrote {out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
