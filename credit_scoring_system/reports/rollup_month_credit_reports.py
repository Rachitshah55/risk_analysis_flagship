# ========== BEGIN: rollup_month_credit_reports.py ==========
import os 
import json 
import calendar
import pandas as pd
import mlflow
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "docs_global" / "reports" / "credit"
MON = ROOT / "docs_global" / "monitoring" / "credit"

def _month_span(year: int, month: int):
    start = datetime(year, month, 1)
    end_day = calendar.monthrange(year, month)[1]
    days = [datetime(year, month, d).strftime("%Y-%m-%d") for d in range(1, end_day + 1)]
    return days

def _read_kpis(day_folder: Path) -> dict | None:
    p = day_folder / "kpis.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None

def _read_drift(day: str) -> pd.DataFrame | None:
    p = MON / day / "drift_summary.csv"
    if p.exists():
        try:
            df = pd.read_csv(p)
            df["report_date"] = day
            return df
        except Exception:
            return None
    return None

def _alert_flag(day: str) -> int:
    return int((MON / day / "alert.txt").exists())

def summarize_month(year: int, month: int) -> dict:
    days = _month_span(year, month)
    day_folders = [REPORTS / d for d in days if (REPORTS / d).exists()]
    kpi_list, drift_frames, alerts = [], [], 0

    for d in days:
        if (REPORTS / d).exists():
            k = _read_kpis(REPORTS / d)
            if k: kpi_list.append({"date": d, **k})
        dr = _read_drift(d)
        if isinstance(dr, pd.DataFrame): drift_frames.append(dr)
        alerts += _alert_flag(d)

    kdf = pd.DataFrame(kpi_list)
    ddf = pd.concat(drift_frames, ignore_index=True) if drift_frames else pd.DataFrame()

    max_psi = float(pd.to_numeric(ddf["psi"], errors="coerce").dropna().max()) if "psi" in ddf.columns else None
    avg_psi = float(pd.to_numeric(ddf["psi"], errors="coerce").dropna().mean()) if "psi" in ddf.columns else None

    top_drifted = None
    if not ddf.empty and {"feature","psi"}.issubset(ddf.columns):
        top_drifted = (ddf.groupby("feature")["psi"].mean().sort_values(ascending=False).head(5)).reset_index()

    summary = {
        "year": year, "month": month, "days_with_reports": len(day_folders),
        "alert_days": int(alerts),
        "max_psi": max_psi, "avg_psi": avg_psi,
        "avg_pd_mean": float(pd.to_numeric(kdf["avg_pd_today"], errors="coerce").dropna().mean()) if "avg_pd_today" in kdf.columns else None,
        "avg_el_total": float(pd.to_numeric(kdf["el_total_today"], errors="coerce").dropna().mean()) if "el_total_today" in kdf.columns else None
    }
    return {"kpis_df": kdf, "drift_df": ddf, "top_drifted": top_drifted, "summary": summary}

def write_html(year: int, month: int, agg: dict) -> Path:
    outdir = REPORTS / f"{year:04d}-{month:02d}"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "credit_monthly_summary.html"

    def _tbl(df: pd.DataFrame, title: str) -> str:
        if df is None or df.empty: return f"<h3>{title}</h3><p>No data</p>"
        return f"<h3>{title}</h3>" + df.to_html(index=False)

    s = agg["summary"]
    html = f"""
    <html><head><meta charset="utf-8"><title>Credit Monthly Summary {year}-{month:02d}</title></head>
    <body>
    <h1>Credit Monthly Summary — {year}-{month:02d}</h1>
    <h2>Executive Summary</h2>
    <ul>
        <li>Days with reports: {s['days_with_reports']}</li>
        <li>Alert days: {s['alert_days']}</li>
        <li>Max PSI: {s['max_psi']}</li>
        <li>Avg PSI: {s['avg_psi']}</li>
        <li>Avg PD (mean of daily): {s['avg_pd_mean']}</li>
        <li>Avg EL (mean of daily totals): {s['avg_el_total']}</li>
    </ul>
    { _tbl(agg['top_drifted'], 'Top Drifted Features (mean PSI)') }
    { _tbl(agg['kpis_df'], 'Daily KPIs (per day)') }
    </body></html>
    """
    out.write_text(html, encoding="utf-8")
    return out

def main(year: int | None = None, month: int | None = None):
    today = datetime.today()
    year = year or today.year
    month = month or today.month
    agg = summarize_month(year, month)
    out = write_html(year, month, agg)
    # MLflow
    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", f"file:///{(ROOT/'mlruns').as_posix()}"))
    exp = mlflow.set_experiment("credit_stage6_monthly_rollup")
    with mlflow.start_run(run_name=f"credit_monthly_{year}-{month:02d}", experiment_id=exp.experiment_id):
        s = agg["summary"]
        for k, v in s.items():
            if isinstance(v, (int, float)):
                mlflow.log_metric(str(k), float(v))
        mlflow.log_artifact(str(out))
    print(f"[OK] Monthly summary: {out}")

if __name__ == "__main__":
    main()
# =========== END: rollup_month_credit_reports.py ===========