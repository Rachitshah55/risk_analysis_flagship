# ===== BEGIN: monitor_fraud_api_logs.py =====
import os, json, argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# -----------------------
# Aliases & helper utils
# -----------------------
CANON = {
    "proba": ["proba", "prob", "score", "p_fraud", "fraud_proba", "model_score"],
    "latency_ms": ["latency_ms", "latency", "elapsed_ms"]
}
CATEGORICAL_CANDS = ["country", "device_id"]
NUMERIC_BASE = ["amount", "hour_of_day"]  # always try these

def first_present(df: pd.DataFrame, names):
    for n in names:
        if n in df.columns:
            return n
    return None

def safe_pct(df: pd.DataFrame, col: str, val: str) -> float:
    if col not in df.columns:
        return 0.0
    s = pd.Series(df[col]).astype(str).str.lower()
    return float(np.mean(s == val))

def safe_num_mean(df: pd.DataFrame, col: str) -> float:
    if not col or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").dropna().mean() or 0.0)

def safe_quantile(df: pd.DataFrame, col: str, q: float) -> float:
    if not col or col not in df.columns:
        return 0.0
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return 0.0
    return float(s.quantile(q))

def psi_numeric(ref, cur, buckets=10, eps=1e-6):
    ref = pd.Series(ref).dropna().astype(float)
    cur = pd.Series(cur).dropna().astype(float)
    if ref.empty or cur.empty:
        return np.nan
    qs = np.linspace(0, 1, buckets + 1)
    edges = np.unique(np.quantile(ref, qs))
    if len(edges) < 2:
        return np.nan
    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)
    ref_pct = (ref_counts + eps) / (ref_counts.sum() + eps * len(ref_counts))
    cur_pct = (cur_counts + eps) / (cur_counts.sum() + eps * len(cur_counts))
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))

def psi_categorical(ref, cur, eps=1e-6):
    # Frequency PSI over union of categories
    ref = pd.Series(ref).dropna().astype(str)
    cur = pd.Series(cur).dropna().astype(str)
    if ref.empty or cur.empty:
        return np.nan
    cats = sorted(set(ref.unique()).union(set(cur.unique())))
    ref_counts = ref.value_counts().reindex(cats).fillna(0).values
    cur_counts = cur.value_counts().reindex(cats).fillna(0).values
    ref_pct = (ref_counts + eps) / (ref_counts.sum() + eps * len(ref_counts))
    cur_pct = (cur_counts + eps) / (cur_counts.sum() + eps * len(cur_counts))
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))

def build_evidently_report(ref_df, cur_df, cols, out_html):
    """
    Generate Evidently HTML drift report (v0.7+ API compatible).
    Falls back gracefully if metrics or imports fail.
    """
    try:
        from evidently import Report
        from evidently.metric_preset import DataDriftPreset
        rpt = Report(metrics=[DataDriftPreset()])
        rpt.run(reference_data=ref_df[cols], current_data=cur_df[cols])
        rpt.save_html(out_html)
        return True
    except Exception as e:
        print(f"[WARN] Evidently 0.7+ Report failed: {e}")
        # minimal fallback: write a simple HTML table
        try:
            drift = ref_df[cols].describe().to_html() + cur_df[cols].describe().to_html()
            with open(out_html, "w", encoding="utf-8") as f:
                f.write(f"<h2>Fallback Drift Summary</h2>{drift}")
            return True
        except Exception as inner:
            print(f"[WARN] Fallback HTML failed: {inner}")
            return False


def load_day(path: Path):
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            tx = obj.get("tx", {})
            rows.append({
                "amount": tx.get("amount"),
                "hour_of_day": tx.get("hour_of_day"),
                "country": tx.get("country"),
                "device_id": tx.get("device_id"),
                "decision": obj.get("decision"),
                "proba": obj.get("proba"),
                "latency_ms": obj.get("latency_ms"),
                "rules_hit": ",".join(obj.get("rules_hit") or []),
                "model_ts": obj.get("model_ts") or obj.get("model_timestamp")
            })
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="CI smoke test mode (synthetic two-day frames).")
    args = ap.parse_args()

    root = Path(r"C:\DevProjects\risk_analysis_flagship")
    logs_dir = root / r"fraud_detection_system\api\logs"

    if args.dry_run:
        ref = pd.DataFrame({
            "amount":[100,120,90,300],
            "hour_of_day":[9,12,15,23],
            "proba":[0.02,0.05,0.10,0.30],
            "latency_ms":[8,9,10,12],
            "decision":["allow","allow","review","flag"],
            "country":["US","US","CA","IN"],
            "device_id":["A","A","B","C"],
        })
        cur = pd.DataFrame({
            "amount":[110,140,80,500],
            "hour_of_day":[8,12,18,1],
            "proba":[0.03,0.06,0.12,0.40],
            "latency_ms":[9,10,12,15],
            "decision":["allow","review","review","flag"],
            "country":["US","GB","CA","IN"],
            "device_id":["A","B","B","D"],
        })
        ref_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        out_dir = root / f"docs_global/monitoring/fraud/{datetime.now():%Y-%m-%d}"
    else:
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        ref = load_day(logs_dir / f"{yesterday}.jsonl")
        cur = load_day(logs_dir / f"{today}.jsonl")
        ref_date = f"{yesterday[:4]}-{yesterday[4:6]}-{yesterday[6:]}"
        out_dir = root / f"docs_global/monitoring/fraud/{datetime.now():%Y-%m-%d}"

    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve aliases for KPI & PSI
    proba_col   = first_present(cur, CANON["proba"]) or first_present(ref, CANON["proba"])
    latency_col = first_present(cur, CANON["latency_ms"]) or first_present(ref, CANON["latency_ms"])

    # -----------------------
    # Operational KPIs
    # -----------------------
    n = len(cur)
    flagged_rate = safe_pct(cur, "decision", "flag") if n else 0.0
    review_rate  = safe_pct(cur, "decision", "review") if n else 0.0
    mean_proba   = safe_num_mean(cur, proba_col)
    p95_latency  = safe_quantile(cur, latency_col, 0.95)

    # -----------------------
    # Drift summary (numeric + categorical)
    # -----------------------
    psi_rows = []

    # Numeric candidates = base + resolved aliases (present in BOTH days)
    numeric_candidates = []
    for base in NUMERIC_BASE:
        if base in ref.columns and base in cur.columns:
            numeric_candidates.append(base)
    if proba_col and (proba_col in ref.columns) and (proba_col in cur.columns):
        numeric_candidates.append(proba_col)
    if latency_col and (latency_col in ref.columns) and (latency_col in cur.columns):
        numeric_candidates.append(latency_col)

    # Deduplicate while preserving order
    seen = set()
    numeric_candidates = [c for c in numeric_candidates if not (c in seen or seen.add(c))]

    for c in numeric_candidates:
        psi_rows.append({"feature": c, "type": "numeric", "psi": psi_numeric(ref[c], cur[c])})

    # Categorical drift (frequency PSI)
    for c in CATEGORICAL_CANDS:
        if c in ref.columns and c in cur.columns:
            psi_rows.append({"feature": c, "type": "categorical", "psi": psi_categorical(ref[c], cur[c])})

    psi_df = pd.DataFrame(psi_rows)
    if not psi_df.empty:
        psi_df = psi_df.sort_values(["psi", "feature"], ascending=[False, True])
    psi_df.to_csv(out_dir / "drift_summary.csv", index=False)

    # -----------------------
    # Evidently HTML (numeric only; safe subset)
    # -----------------------
    used_cols = [c for c in ["amount", "hour_of_day"] if c in ref.columns and c in cur.columns]
    if used_cols:
        build_evidently_report(ref, cur, used_cols, (out_dir / "drift_report.html").as_posix())

    # -----------------------
    # Alerts
    # -----------------------
    alert_lines = []

    # PSI alert (any feature >= 0.25)
    if not psi_df.empty and psi_df["psi"].fillna(0).ge(0.25).any():
        worst = psi_df.sort_values("psi", ascending=False).head(5)
        alert_lines.append("DRIFT ALERT (PSI ≥ 0.25)\n" + worst.to_string(index=False))

    # Latency vs yesterday baseline
    if latency_col and (latency_col in ref.columns):
        ref_p95 = safe_quantile(ref, latency_col, 0.95)
        if p95_latency > max(250.0, ref_p95 * 1.5):
            alert_lines.append(f"LATENCY ALERT: p95 {p95_latency:.1f} ms vs {ref_p95:.1f} ms baseline")

    # Flagged-rate anomaly vs yesterday baseline
    if "decision" in ref.columns and len(ref):
        ref_flag = safe_pct(ref, "decision", "flag")
        if ref_flag > 0 and (flagged_rate > ref_flag * 1.5 or flagged_rate < ref_flag * 0.5):
            alert_lines.append(f"FLAGGED-RATE ALERT: today {flagged_rate:.3f} vs yesterday {ref_flag:.3f}")

    if alert_lines:
        with open(out_dir / "alert.txt", "w", encoding="utf-8") as f:
            f.write("\n\n".join(alert_lines))

    # -----------------------
    # metrics.json (for dashboards)
    # -----------------------
    metrics = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "requests": int(n),
        "flagged_rate": flagged_rate,
        "review_rate": review_rate,
        "mean_proba": mean_proba,
        "p95_latency_ms": p95_latency,
        "ref_date": ref_date,
        "proba_col": proba_col or "",
        "latency_col": latency_col or ""
    }
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Note missing columns to aid API logging alignment
    expected = ["amount", "hour_of_day", "decision"] + CANON["proba"] + CANON["latency_ms"] + CATEGORICAL_CANDS
    missing_cur = [c for c in expected if c not in cur.columns]
    with open(out_dir / "missing_columns.txt", "w", encoding="utf-8") as f:
        f.write("Missing in TODAY (current): " + ", ".join(missing_cur) + "\n")

    # -----------------------
    # MLflow logging (best-effort)
    # -----------------------
    try:
        import mlflow
        mlflow.set_experiment("fraud_stage5_monitoring")
        with mlflow.start_run(run_name=f"fraud_monitor_{datetime.now():%Y%m%d_%H%M%S}"):
            if not psi_df.empty:
                for _, r in psi_df.iterrows():
                    mlflow.log_metric(f"psi_{r['feature']}", float(r["psi"]) if pd.notna(r["psi"]) else 0.0)
            mlflow.log_metric("flagged_rate", flagged_rate)
            mlflow.log_metric("review_rate", review_rate)
            mlflow.log_metric("proba_mean", mean_proba)
            mlflow.log_metric("latency_p95_ms", p95_latency)
            mlflow.log_artifact((out_dir / "drift_summary.csv").as_posix())
            if (out_dir / "drift_report.html").exists(): mlflow.log_artifact((out_dir / "drift_report.html").as_posix())
            if (out_dir / "alert.txt").exists(): mlflow.log_artifact((out_dir / "alert.txt").as_posix())
            mlflow.log_artifact((out_dir / "metrics.json").as_posix())
            mlflow.log_artifact((out_dir / "missing_columns.txt").as_posix())
    except Exception as e:
        print(f"[WARN] MLflow logging skipped: {e}")

    print(f"[OK] Fraud monitoring written to: {out_dir}")

if __name__ == "__main__":
    main()
# ===== END: monitor_fraud_api_logs.py =====
