# shared_env/bi/export_for_bi.py
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
import argparse
import pandas as pd
from pandas.errors import EmptyDataError, ParserError

ROOT = Path(__file__).resolve().parents[2]  # repo root
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"

def _dstr(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")

def _ymd(d: datetime) -> str:
    return d.strftime("%Y%m%d")

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def _is_nonempty_file(p: Path) -> bool:
    return p.exists() and p.is_file() and p.stat().st_size > 0

def _append_csv_safely(df: pd.DataFrame, out_csv: Path, pk_cols: list[str] | None = None):
    _ensure_dir(out_csv.parent)
    if out_csv.exists():
        try:
            old = pd.read_csv(out_csv)
            df = pd.concat([old, df], ignore_index=True)
            if pk_cols:
                df = df.drop_duplicates(subset=pk_cols, keep="last")
            else:
                df = df.drop_duplicates(keep="last")
        except Exception as e:
            print(f"[WARN] Could not read existing {out_csv.name}: {e}. Overwriting with new rows.")
    df.to_csv(out_csv, index=False)

def _flatten_json_to_row(js: dict, extra: dict) -> pd.DataFrame:
    flat = {}
    def walk(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(f"{prefix}{k}.", v)
        elif isinstance(obj, list):
            flat[prefix[:-1]] = json.dumps(obj)
        else:
            flat[prefix[:-1]] = obj
    walk("", js)
    flat.update(extra)
    return pd.DataFrame([flat])

# ---------- CREDIT ----------
def export_credit_for_bi(run_date: datetime):
    day = _dstr(run_date)
    ymd = _ymd(run_date)

    seg_parquet = ROOT / f"credit_scoring_system/outputs/scoring/segment_rollups_{ymd}.parquet"
    seg_csv_out = ROOT / f"docs_global/bi/credit/segment_rollups_{ymd}.csv"
    if seg_parquet.exists():
        try:
            df_seg = pd.read_parquet(seg_parquet)
            _ensure_dir(seg_csv_out.parent)
            df_seg.to_csv(seg_csv_out, index=False)
            print(f"[OK] Credit segment rollups → {seg_csv_out}")
        except Exception as e:
            print(f"[WARN] Could not read {seg_parquet.name}: {e}. Skipping segment export for {day}.")
    else:
        print(f"[INFO] Missing credit segment parquet for {day} — skipping.")

    kpis_json = ROOT / f"docs_global/reports/credit/{day}/kpis.json"
    kpis_daily_out = ROOT / "docs_global/bi/credit/kpis_daily.csv"
    if _is_nonempty_file(kpis_json):
        try:
            with open(kpis_json, "r", encoding="utf-8") as f:
                js = json.load(f)
            row = _flatten_json_to_row(js, {"date": day, "system": "credit"})
            _append_csv_safely(row, kpis_daily_out, pk_cols=["date","system"])
            print(f"[OK] Credit KPIs appended → {kpis_daily_out}")
        except json.JSONDecodeError as e:
            print(f"[WARN] Malformed credit kpis.json for {day}: {e}. Skipping append.")
    else:
        print(f"[INFO] Missing/empty credit kpis.json for {day} — skipping.")

# ---------- FRAUD ----------
def export_fraud_for_bi(run_date: datetime):
    day = _dstr(run_date)
    day_dir = ROOT / f"docs_global/monitoring/fraud/{day}"
    raw_out = ROOT / f"docs_global/bi/fraud/raw/{day}"
    _ensure_dir(raw_out)

    # Copy drift_summary.csv (if present & nonempty)
    drift_csv = day_dir / "drift_summary.csv"
    if _is_nonempty_file(drift_csv):
        try:
            df = pd.read_csv(drift_csv)
            df.to_csv(raw_out / "drift_summary.csv", index=False)
            print(f"[OK] Fraud drift_summary copied → {raw_out / 'drift_summary.csv'}")
        except (EmptyDataError, ParserError) as e:
            print(f"[INFO] drift_summary.csv empty or invalid for {day}: {e}. Skipping.")
        except Exception as e:
            print(f"[WARN] Could not copy drift_summary.csv for {day}: {e}.")
    else:
        if drift_csv.exists():
            print(f"[INFO] drift_summary.csv exists but empty for {day} — skipping.")
        else:
            print(f"[INFO] No drift_summary.csv for {day} — skipping.")

    # Flatten metrics.json → metrics_daily.csv
    metrics_json = day_dir / "metrics.json"
    metrics_daily_out = ROOT / "docs_global/bi/fraud/metrics_daily.csv"
    if _is_nonempty_file(metrics_json):
        try:
            with open(metrics_json, "r", encoding="utf-8") as f:
                js = json.load(f)
            row = _flatten_json_to_row(js, {"date": day, "system": "fraud"})
            _append_csv_safely(row, metrics_daily_out, pk_cols=["date","system"])
            print(f"[OK] Fraud metrics appended → {metrics_daily_out}")
        except json.JSONDecodeError as e:
            print(f"[WARN] Malformed fraud metrics.json for {day}: {e}. Skipping append.")
    else:
        print(f"[INFO] Missing/empty fraud metrics.json for {day} — skipping.")

    # Append fraud KPIs from the daily report
    kpis_json = ROOT / f"docs_global/reports/fraud/{day}/kpis.json"
    kpis_daily_out = ROOT / "docs_global/bi/fraud/kpis_daily.csv"
    if _is_nonempty_file(kpis_json):
        try:
            with open(kpis_json, "r", encoding="utf-8") as f:
                js = json.load(f)
            row = _flatten_json_to_row(js, {"date": day, "system": "fraud"})
            _append_csv_safely(row, kpis_daily_out, pk_cols=["date","system"])
            print(f"[OK] Fraud KPIs appended → {kpis_daily_out}")
        except json.JSONDecodeError as e:
            print(f"[WARN] Malformed fraud kpis.json for {day}: {e}. Skipping append.")
    else:
        print(f"[INFO] Missing/empty fraud kpis.json for {day} — skipping.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD; default=today", default=None)
    args = ap.parse_args()
    run_date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()

    # Export both systems so Tableau refresh sees new rows
    export_credit_for_bi(run_date)
    export_fraud_for_bi(run_date)
    print(f"[OK] BI exports for {run_date:%Y-%m-%d} complete.")

if __name__ == "__main__":
    main()
