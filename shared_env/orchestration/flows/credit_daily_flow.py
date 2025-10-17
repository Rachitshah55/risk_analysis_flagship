from pathlib import Path
import subprocess

# repo_root = .../shared_env/orchestration/flows → parents[3] = repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")

def run_rel(rel_path: str):
    script = REPO_ROOT / rel_path
    subprocess.check_call([PY, str(script)], cwd=str(REPO_ROOT))

def main():
    # Stage 5 (credit) – daily monitor
    run_rel("shared_env/monitoring/monitor_credit_drift.py")
    # Stage 4 (credit) – batch scoring
    run_rel("credit_scoring_system/scripts/score_credit_portfolio.py")
    # Stage 6 (credit) – daily HTML report
    run_rel("credit_scoring_system/reports/run_daily_credit_report.py")

if __name__ == "__main__":
    main()


