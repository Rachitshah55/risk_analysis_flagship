import os
import sys
import json
import subprocess
from datetime import datetime, timedelta, date
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
MON_CREDIT = ROOT / "docs_global" / "monitoring" / "credit"
SCORING_OUT = ROOT / "credit_scoring_system" / "outputs" / "scoring"
REPORTS_BASE = ROOT / "docs_global" / "reports" / "credit"

def _coerce_date(dstr: str | None) -> date:
    if dstr is None or str(dstr).strip().lower() in {"", "today"}:
        return date.today()
    return datetime.strptime(dstr, "%Y-%m-%d").date()

def _day_dir(d: date) -> Path:
    return MON_CREDIT / d.strftime("%Y-%m-%d")

def _find_scoring_for(d: date, kind: str) -> Path | None:
    pat = f"{kind}_{d.strftime('%Y%m%d')}.parquet"
    p = SCORING_OUT / pat
    return p if p.exists() else None

def load_daily(day: str | None = None) -> dict:
    d = _coerce_date(day)
    ddir = _day_dir(d)
    out = {"day": d, "drift_df": None, "calibration_png": None, "pd_mean": None, "el_total": None, "el_by_segment_df": None}

    drift_csv = ddir / "drift_summary.csv"
    if drift_csv.exists():
        try:
            out["drift_df"] = pd.read_csv(drift_csv)
        except Exception:
            out["drift_df"] = None

    for name in ("calibration_plot.png", "calibration_plot.jpg", "calibration_plot.jpeg"):
        p = ddir / name
        if p.exists():
            out["calibration_png"] = p
            break

    pd_parquet = _find_scoring_for(d, "pd_scores")
    if pd_parquet is not None:
        try:
            df_pd = pd.read_parquet(pd_parquet)
            pd_col = next((c for c in df_pd.columns if str(c).lower() in {"pd", "prob_default", "probability_default"}), None)
            if pd_col:
                out["pd_mean"] = float(pd.to_numeric(df_pd[pd_col], errors="coerce").dropna().mean())
        except Exception:
            pass

    seg_parquet = _find_scoring_for(d, "segment_rollups")
    if seg_parquet is not None:
        try:
            seg = pd.read_parquet(seg_parquet)
            el_col = next((c for c in seg.columns if str(c).lower() in {"el", "expected_loss"}), None)
            if el_col:
                out["el_total"] = float(pd.to_numeric(seg[el_col], errors="coerce").dropna().sum())
            out["el_by_segment_df"] = seg
        except Exception:
            pass

    return out

def load_trailing(days: int = 7, end_day: str | None = None) -> dict:
    end_d = _coerce_date(end_day)
    psi_frames, pd_list, el_list = [], [], []
    found = 0
    for i in range(1, days + 1):
        d = end_d - timedelta(days=i)
        info = load_daily(d.strftime("%Y-%m-%d"))
        if info["drift_df"] is not None:
            psi_frames.append(info["drift_df"].assign(report_date=d.strftime("%Y-%m-%d")))
        if info["pd_mean"] is not None:
            pd_list.append(info["pd_mean"])
        if info["el_total"] is not None:
            el_list.append(info["el_total"])
        if (info["drift_df"] is not None) or (info["pd_mean"] is not None) or (info["el_total"] is not None):
            found += 1
    return {"days_found": found, "psi_frames": psi_frames, "pd_list": pd_list, "el_list": el_list}

def kpi_today_vs_trailing(today: dict, trailing: dict) -> dict:
    avg_pd_today = today.get("pd_mean")
    el_total_today = today.get("el_total")

    max_psi_today = None
    if isinstance(today.get("drift_df"), pd.DataFrame) and "psi" in today["drift_df"].columns:
        try:
            max_psi_today = float(pd.to_numeric(today["drift_df"]["psi"], errors="coerce").dropna().max())
        except Exception:
            max_psi_today = None

    trailing_avg_pd = float(pd.Series(trailing["pd_list"]).mean()) if trailing["pd_list"] else None
    trailing_avg_el = float(pd.Series(trailing["el_list"]).mean()) if trailing["el_list"] else None

    trailing_mean_psi = trailing_max_psi = None
    if trailing["psi_frames"]:
        tdf = pd.concat(trailing["psi_frames"], ignore_index=True)
        if "psi" in tdf.columns:
            series = pd.to_numeric(tdf["psi"], errors="coerce").dropna()
            if not series.empty:
                trailing_mean_psi = float(series.mean())
                trailing_max_psi = float(series.max())

    delta_el_vs_7d = None
    if (el_total_today is not None) and (trailing_avg_el is not None):
        delta_el_vs_7d = float(el_total_today - trailing_avg_el)

    delta_pd_vs_7d = None
    if (avg_pd_today is not None) and (trailing_avg_pd is not None):
        delta_pd_vs_7d = float(avg_pd_today - trailing_avg_pd)

    return {
        "avg_pd_today": avg_pd_today,
        "el_total_today": el_total_today,
        "max_psi_today": max_psi_today,
        "trailing_avg_pd": trailing_avg_pd,
        "trailing_avg_el": trailing_avg_el,
        "trailing_mean_psi": trailing_mean_psi,
        "trailing_max_psi": trailing_max_psi,
        "delta_el_vs_7d": delta_el_vs_7d,
        "delta_pd_vs_7d": delta_pd_vs_7d,
    }

def el_by_segment(day: str | None = None) -> pd.DataFrame | None:
    d = _coerce_date(day)
    seg = _find_scoring_for(d, "segment_rollups")
    if seg and seg.exists():
        try:
            return pd.read_parquet(seg)
        except Exception:
            return None
    return None

def ensure_outdir(day: str | None = None) -> Path:
    d = _coerce_date(day)
    outdir = REPORTS_BASE / d.strftime("%Y-%m-%d")
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir

def render_nbconvert(day: str | None = None, to_pdf: bool = False, timeout: int = 600) -> dict:
    d = _coerce_date(day)
    outdir = ensure_outdir(d.strftime("%Y-%m-%d"))
    nb = ROOT / "credit_scoring_system" / "reports" / "templates" / "credit_daily_report.ipynb"
    if not nb.exists():
        raise FileNotFoundError(f"Template notebook missing: {nb}")

    env = os.environ.copy()
    env["REPORT_DATE"] = d.strftime("%Y-%m-%d")
    env["PROJECT_ROOT"] = str(ROOT)                           
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH","")  

    html_path = outdir / "credit_daily_report.html"
    cmd_html = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--execute", str(nb),
        "--to", "html",
        "--output", "credit_daily_report.html",
        "--output-dir", str(outdir),
        f"--ExecutePreprocessor.timeout={timeout}",
    ]
    subprocess.run(cmd_html, check=True, env=env)

    pdf_path = None
    if to_pdf:
        try:
            cmd_pdf = [
                sys.executable, "-m", "jupyter", "nbconvert",
                "--execute", str(nb),
                "--to", "webpdf",
                "--output", "credit_daily_report.pdf",
                "--output-dir", str(outdir),
                f"--ExecutePreprocessor.timeout={timeout}",
            ]
            subprocess.run(cmd_pdf, check=True, env=env)
            pdf_path = outdir / "credit_daily_report.pdf"
        except Exception:
            pdf_path = None

    return {"html": html_path, "pdf": pdf_path}