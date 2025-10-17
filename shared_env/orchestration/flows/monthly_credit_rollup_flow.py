from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[3]
PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")

def main():
    # EOM derived roll-up (Stage 6)
    target = REPO_ROOT / "credit_scoring_system/reports/rollup_month_credit_reports.py"
    subprocess.check_call([PY, str(target)], cwd=str(REPO_ROOT))

if __name__ == "__main__":
    main()