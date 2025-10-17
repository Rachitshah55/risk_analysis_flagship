# C:\DevProjects\risk_analysis_flagship\fraud_detection_system\reports\run_daily_fraud_report.py
from __future__ import annotations
from pathlib import Path
import argparse, os, json, datetime as dt
import mlflow
import pandas as pd

from utils.fraud_report_utils import (
    resolve_paths, load_jsonl_safe, load_monitor_artifacts,
    compute_kpis, save_json, render_nb_or_fallback
)

# FIX: this file sits at repo_root/fraud_detection_system/reports/run_daily_fraud_report.py
# reports -> (0), fraud_detection_system -> (1), REPO_ROOT -> (2)
REPO_ROOT = Path(__file__).resolve().parents[2]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (default: today)", default=None)
    p.add_argument("--per_fraud_usd", type=float, default=200.0,
                   help="Assumed avoided loss per blocked fraud if labels missing")
    return p.parse_args()

def to_date(s: str | None) -> dt.date:
    if not s:
        return dt.date.today()
    return dt.datetime.strptime(s, "%Y-%m-%d").date()

def main():
    args = parse_args()
    report_date = to_date(args.date)
    paths = resolve_paths(REPO_ROOT, report_date)

    # Load inputs
    df_logs = load_jsonl_safe(paths["logs_jsonl"])
    drift_df, drift_metrics = load_monitor_artifacts(paths["monitor_dir"])

    # Compute KPIs
    kpis = compute_kpis(df_logs, drift_metrics, per_fraud_usd=args.per_fraud_usd)
    save_json(paths["kpis_json"], kpis)

    # Render HTML (nbconvert preferred; fallback built-in)
    work_dir = paths["out_dir"]
    mode = render_nb_or_fallback(paths["template_ipynb"], work_dir, paths["html_out"])

    # MLflow logging
    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        f"file:///{(REPO_ROOT/'mlruns').as_posix()}"
    )
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("fraud_stage7_daily_reporting")

    tags = {
        "stage": "7",
        "report_date": report_date.strftime("%Y-%m-%d"),
        "renderer": mode,
    }

    with mlflow.start_run(tags=tags, run_name=f"fraud_daily_{report_date:%Y%m%d}"):
        for key in [
            "total_txns","flagged","flagged_pct",
            "p50_latency_ms","p95_latency_ms",
            "precision","recall","fpr","fraud_prevented_usd"
        ]:
            val = kpis.get(key)
            if isinstance(val, (int, float)) and val is not None:
                mlflow.log_metric(key, float(val))

        mlflow.log_param("arms_present", "1" if kpis.get("arms") else "0")
        mlflow.log_param("drift_metrics_present", str(kpis.get("drift_metrics_present", False)))

        mlflow.log_artifact(str(paths["kpis_json"]), artifact_path="report")
        if paths["html_out"].exists():
            mlflow.log_artifact(str(paths["html_out"]), artifact_path="report")
        drift_csv = paths["monitor_dir"] / "drift_summary.csv"
        if drift_csv.exists():
            mlflow.log_artifact(str(drift_csv), artifact_path="monitor")

    print(f"[OK] Fraud daily report written to: {paths['html_out']}")
    print(f"[OK] KPIs saved to: {paths['kpis_json']}")
    if len(df_logs) == 0:
        print("[WARN] No JSONL logs for today — report includes empty sections.")

if __name__ == "__main__":
    main()
