from pathlib import Path
import subprocess, os, sys, datetime

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
MON = ROOT / "shared_env" / "monitoring" / "monitor_fraud_api_logs.py"
EVAL = ROOT / "fraud_detection_system" / "analysis" / "evaluate_ab_and_promote.py"

def run_step(title, args):
    print(f"[RUN] {title}")
    r = subprocess.run([str(PY), str(args)], cwd=str(ROOT))
    if r.returncode != 0:
        print(f"[WARN] Step failed: {title}")
    else:
        print(f"[OK] {title}")

def main():
    print("[Chain] Fraud Stage 5: Monitor API logs...")
    run_step("monitor_fraud_api_logs.py", MON)

    # Optional: if you're canary-testing today AND you want a daily summary
    traffic_mode = os.environ.get("FRAUD_TRAFFIC_MODE", "").lower()
    if traffic_mode == "ab" and EVAL.exists():
        print("[Chain] Fraud Stage 6: A/B daily summary (no changes to .env).")
        run_step("evaluate_ab_and_promote.py", EVAL)
    else:
        print("[Skip] A/B summary (not in AB mode).")

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    out_dir = ROOT / "docs_global" / "monitoring" / "fraud" / today
    print(f"[INFO] Monitoring output folder: {out_dir}")

if __name__ == "__main__":
    main()
# ===== END: run_fraud_daily_full.py =====
