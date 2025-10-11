# C:\DevProjects\risk_analysis_flagship\credit_scoring_system\reports\run_daily_credit_report.py
# Fresh full version — Stage 6 daily credit report runner

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import date

# --------------------------------------------------------------------------------------
# Ensure the project root is on sys.path so "credit_scoring_system" package resolves
# File is at: ...\credit_scoring_system\reports\run_daily_credit_report.py
# parents[0]=reports, [1]=credit_scoring_system, [2]=<project root>
# --------------------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # C:\DevProjects\risk_analysis_flagship
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Deps: mlflow + our report utils
import mlflow  # noqa: E402

from credit_scoring_system.reports.utils.credit_report_utils import (  # noqa: E402
    load_daily,
    load_trailing,
    kpi_today_vs_trailing,
    ensure_outdir,
    render_nbconvert,
)

MON_CREDIT = PROJECT_ROOT / "docs_global" / "monitoring" / "credit"
EXP_NAME = "credit_stage6_daily_reporting"


def _require_stage5_outputs(day_str: str) -> Path:
    """
    Assert Stage 5 daily monitor has produced the required inputs for the given day.
    Returns the day's monitor directory if present; raises FileNotFoundError otherwise.
    """
    day_dir = MON_CREDIT / day_str
    drift_csv = day_dir / "drift_summary.csv"
    if not drift_csv.exists():
        raise FileNotFoundError(
            f"[Stage6] Missing Stage 5 output for {day_str}. "
            f"Expected file not found:\n{drift_csv}\n"
            f"Run Stage 5 monitor first to generate it."
        )
    return day_dir


def _setup_mlflow():
    # Track to local mlruns by default; env var can override
    ml_uri = os.environ.get("MLFLOW_TRACKING_URI", f"file:///{(PROJECT_ROOT / 'mlruns').as_posix()}")
    mlflow.set_tracking_uri(ml_uri)
    exp = mlflow.set_experiment(EXP_NAME)
    return exp


def main(day: str | None = None, to_pdf: bool = False, verbose: bool = True, log_mlflow: bool = True):
    # Resolve target day
    day_str = day or date.today().strftime("%Y-%m-%d")
    if verbose:
        print(f"[Stage6] Credit Daily Report for {day_str}")

    # 0) Hard guard: require Stage 5 outputs for {day}
    day_dir = _require_stage5_outputs(day_str)
    if verbose:
        print(f"[Stage6] Found Stage 5 inputs at: {day_dir}")

    # 1) Load today + trailing window
    today = load_daily(day_str)
    trailing = load_trailing(7, day_str)
    kpis = kpi_today_vs_trailing(today, trailing)
    missing = [k for k in ("avg_pd_today","el_total_today","delta_el_vs_7d") if kpis.get(k) is None]
    if missing:
        print("[Stage6] Note: the following KPIs are None →", missing)
        print("         Ensure these files exist for today:")
        print("         - credit_scoring_system\\outputs\\scoring\\pd_scores_YYYYMMDD.parquet  (must have 'pd')")
        print("         - credit_scoring_system\\outputs\\scoring\\segment_rollups_YYYYMMDD.parquet  (must have 'EL'/'expected_loss')")


    # 2) Persist KPIs (used by monthly roll-up)
    outdir = ensure_outdir(day_str)
    kpis_path = outdir / "kpis.json"
    kpis_path.write_text(json.dumps(kpis, indent=2))
    if verbose:
        non_null = {k: v for k, v in kpis.items() if v is not None}
        print(f"[Stage6] KPIs saved → {kpis_path}")
        print(f"[Stage6] KPIs (non-null): {non_null}")

    # 3) Render notebook → HTML (PDF optional)
    rendered = render_nbconvert(day_str, to_pdf=to_pdf)
    html_path = rendered["html"]
    pdf_path = rendered.get("pdf")
    if verbose:
        print(f"[Stage6] HTML report → {html_path}")
        if pdf_path:
            print(f"[Stage6] PDF report  → {pdf_path}")

    # 4) MLflow logging (optional)
    if log_mlflow:
        exp = _setup_mlflow()
        with mlflow.start_run(run_name=f"credit_daily_{day_str}", experiment_id=exp.experiment_id):
            # numeric metrics only
            for k, v in kpis.items():
                if v is not None and isinstance(v, (int, float)):
                    mlflow.log_metric(k, float(v))
            mlflow.log_artifact(str(html_path))
            if pdf_path:
                mlflow.log_artifact(str(pdf_path))
            mlflow.log_artifact(str(kpis_path))
        if verbose:
            print("[Stage6] MLflow run logged.")

    if verbose:
        print("[Stage6] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 6 — Credit Daily Reporting")
    parser.add_argument("--day", help="Target day as YYYY-MM-DD (defaults to today).")
    parser.add_argument("--pdf", action="store_true", help="Also render PDF via nbconvert webpdf (optional).")
    parser.add_argument(
        "--no-mlflow", action="store_true", help="Skip MLflow logging (still writes HTML + KPIs)."
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce console output.")
    args = parser.parse_args()

    main(
        day=args.day,
        to_pdf=args.pdf,
        verbose=not args.quiet,
        log_mlflow=(not args.no_mlflow),
    )
