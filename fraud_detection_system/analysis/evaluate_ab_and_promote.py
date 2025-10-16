# fraud_detection_system/analysis/evaluate_ab_and_promote.py
from __future__ import annotations
import json, shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LOGS = ROOT / "fraud_detection_system" / "api" / "logs"
REPORT_DIR = ROOT / "docs_global" / "reports" / "fraud" / "ab_tests" / datetime.now().strftime("%Y-%m")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ROOT / "fraud_detection_system" / "models"
PROD_PTR = MODELS / "PROD_POINTER.txt"  # contains absolute path to current prod dir
HISTORY = ROOT / "docs_global" / "releases"
HISTORY.mkdir(parents=True, exist_ok=True)

# (Optional) label join: put labeled CSVs here if available
LABELS_DIR = ROOT / "fraud_detection_system" / "data" / "labels"

def load_logs_for_day(day: str):
    # Load both normal and arm-bearing logs (prod/cand)
    f_main = LOGS / f"{day}.jsonl"
    f_shadow = LOGS / f"{day}_shadow.jsonl"
    dfs = []
    for f in [f_main, f_shadow]:
        if f.exists():
            dfs.append(pd.read_json(f, lines=True))
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def compute_metrics(df: pd.DataFrame, labels: pd.DataFrame|None):
    out = []
    for arm in ["prod", "cand"]:
        d = df[df.get("arm","prod").fillna("prod")==arm].copy()
        if d.empty: 
            continue
        lat = d["latency_ms"] if "latency_ms" in d.columns else pd.Series([], dtype=float)
        p95 = float(np.percentile(lat, 95)) if len(lat) else np.nan
        prec = rec = fpr = np.nan
        if labels is not None and "txn_id" in d.get("payload", pd.Series([{}])).iloc[0]:
            # If you log txn_id inside payload, you can merge here; else keep proxy metrics
            pass
        out.append({"arm": arm, "p95_latency_ms": p95, "precision": prec, "recall": rec, "fpr": fpr})
    return pd.DataFrame(out)

def promote_if_better(summary_csv: Path, cand_dir: Path):
    df = pd.read_csv(summary_csv)
    rowp = df[df.arm=="prod"].iloc[0] if (df.arm=="prod").any() else None
    rowc = df[df.arm=="cand"].iloc[0] if (df.arm=="cand").any() else None
    if rowp is None or rowc is None:
        return False, "Missing arms"
    # Promotion rule (labels optional): prioritize recall, bound FPR, keep latency sane
    ok_latency = (np.isnan(rowc.p95_latency_ms) or np.isnan(rowp.p95_latency_ms) 
                  or rowc.p95_latency_ms <= 2.0 * rowp.p95_latency_ms)
    ok_labels = (np.isnan(rowp.recall) or np.isnan(rowc.recall) or (rowc.recall >= rowp.recall and
                 (np.isnan(rowc.fpr) or np.isnan(rowp.fpr) or rowc.fpr <= rowp.fpr + 0.005)))
    if ok_latency and ok_labels:
        cand_dir = Path(cand_dir).resolve()
        HISTORY.joinpath(f"fraud_PROD_{datetime.now().strftime('%Y%m%d')}.txt").write_text(str(cand_dir))
        PROD_PTR.write_text(str(cand_dir))
        return True, "Promoted"
    return False, "Not promoted"

def main():
    today = datetime.now().strftime("%Y%m%d")
    logs = load_logs_for_day(today)
    if logs.empty:
        print("[WARN] No logs today; cannot evaluate.")
        return
    labels = None
    # Optional: load labels if present (txn_id, is_fraud)
    lbls = sorted(LABELS_DIR.glob("transactions_labels_*.csv"))
    if lbls:
        labels = pd.read_csv(lbls[-1])
    summary = compute_metrics(logs, labels)
    csvp = REPORT_DIR / f"ab_summary_{today}.csv"
    htmlp = REPORT_DIR / f"ab_summary_{today}.html"
    summary.to_csv(csvp, index=False)
    summary.to_html(htmlp, index=False)
    # read candidate dir from env pointer file that you set below
    cand_ptr = ROOT / "fraud_detection_system" / "models" / f"CAND_{today}"
    promoted, msg = promote_if_better(csvp, cand_ptr if cand_ptr.exists() else cand_ptr)
    print(f"[EVAL] {msg}. Summary: {csvp}")

if __name__ == "__main__":
    main()
