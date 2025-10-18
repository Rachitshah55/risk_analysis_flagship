# Orchestrates: Stage 5 (monitor) -> Stage 4 (score) -> Stage 6 (report) -> BI export
from pathlib import Path
import sys
import subprocess
from datetime import datetime

# Ensure repo root on sys.path so "shared_env" imports resolve
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared_env.bi.export_for_bi import export_credit_for_bi  # noqa: E402

PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")

def run_rel(rel_path: str):
    script = REPO_ROOT / rel_path
    print(f"[FLOW] Running: {script}")
    subprocess.check_call([PY, str(script)], cwd=str(REPO_ROOT))

def main():
    # Stage 5 (credit) – daily monitor
    run_rel("shared_env/monitoring/monitor_credit_drift.py")
    # Stage 4 (credit) – batch scoring
    run_rel("credit_scoring_system/scripts/score_credit_portfolio.py")
    # Stage 6 (credit) – daily HTML report
    run_rel("credit_scoring_system/reports/run_daily_credit_report.py")
    # D3) Tableau export (AFTER artifacts exist)
    export_credit_for_bi(datetime.now())
    print("[FLOW] Credit daily flow complete.")

if __name__ == "__main__":
    main()
