# shared_env/orchestration/flows/fraud_daily_flow.py
from pathlib import Path
import subprocess
from datetime import datetime
from shared_env.bi.export_for_bi import export_fraud_for_bi

REPO_ROOT = Path(__file__).resolve().parents[3]
PY = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")

def run_rel(rel_path: str):
    script = REPO_ROOT / rel_path
    subprocess.check_call([PY, str(script)], cwd=str(REPO_ROOT))

def main():
    # Stage 5 (fraud) – monitor logs & compute drift/metrics
    run_rel("shared_env/monitoring/monitor_fraud_api_logs.py")
    # Stage 7 (fraud) – daily HTML report
    run_rel("fraud_detection_system/reports/run_daily_fraud_report.py")

    # D3) Tableau export
    export_fraud_for_bi(datetime.now())

if __name__ == "__main__":
    main()
