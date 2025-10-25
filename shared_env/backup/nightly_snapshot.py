# nightly_snapshot.py — DVC push + zip docs_global reports (daily + EOM)
from pathlib import Path
from datetime import datetime
import subprocess, shutil, sys, json

ROOT = Path(__file__).resolve().parents[2]  # repo root
DOCS = ROOT / "docs_global"
BACKUPS = DOCS / "backups"
REPORTS = DOCS / "reports"

def run(cmd, cwd=None, env=None):
    print(f"[RUN] {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd or ROOT, env=env, capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
    return r.returncode == 0

def zip_dir(arc_path: Path, source_dir: Path):
    if not source_dir.exists():
        print(f"[INFO] skip zip (missing): {source_dir}")
        return None
    # Make zip without extension in make_archive
    base = str(arc_path.with_suffix(""))
    root_dir = str(source_dir)
    shutil.make_archive(base, "zip", root_dir=root_dir)
    print(f"[OK] wrote {arc_path}")
    return arc_path

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    outdir = BACKUPS / today
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) DVC push — data snapshots referenced by runs
    ok = run(["dvc", "push"])
    (outdir / "dvc_push.ok").write_text("1" if ok else "0")

    # 2) Zip all daily reports generated today (credit + fraud)
    todays_reports = REPORTS / "credit" / today
    todays_reports_f = REPORTS / "fraud" / today
    arc_daily = outdir / f"reports_daily_{today}.zip"
    # Build a temp staging dir combining both systems (if present)
    staging = outdir / f"staging_{today}"
    staging.mkdir(exist_ok=True)
    for p in [todays_reports, todays_reports_f]:
        if p.exists():
            target = staging / p.parts[-2] / p.parts[-1]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(p, target, dirs_exist_ok=True)
    zip_dir(arc_daily, staging)
    shutil.rmtree(staging, ignore_errors=True)

    # 3) Zip EOM summaries for the current month (credit + fraud)
    month_dir_credit = REPORTS / "credit" / month
    month_dir_fraud = REPORTS / "fraud" / month
    arc_month = outdir / f"reports_monthly_{month}.zip"
    staging_m = outdir / f"staging_{month}"
    staging_m.mkdir(exist_ok=True)
    for p in [month_dir_credit, month_dir_fraud]:
        if p.exists():
            target = staging_m / p.parts[-2] / p.parts[-1]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(p, target, dirs_exist_ok=True)
    zip_dir(arc_month, staging_m)
    shutil.rmtree(staging_m, ignore_errors=True)

    # 4) Log file
    log = {
        "date": today,
        "month": month,
        "dvc_push": ok,
        "daily_zip": str(arc_daily) if arc_daily.exists() else None,
        "monthly_zip": str(arc_month) if arc_month.exists() else None,
    }
    (outdir / "backup_log.json").write_text(json.dumps(log, indent=2))
    print("[DONE] Nightly snapshot complete.")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
