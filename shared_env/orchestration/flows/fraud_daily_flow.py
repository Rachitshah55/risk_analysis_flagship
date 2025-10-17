from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[3]
PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")

def run_rel(rel_path: str):
    script = REPO_ROOT / rel_path
    subprocess.check_call([PY, str(script)], cwd=str(REPO_ROOT))

def main():
    # Stage 5 – fraud daily drift/ops metrics from API JSONL
    run_rel("shared_env/monitoring/monitor_fraud_api_logs.py")
    # Stage 7 – fraud daily HTML report
    run_rel("fraud_detection_system/reports/run_daily_fraud_report.py")

if __name__ == "__main__":
    main()
