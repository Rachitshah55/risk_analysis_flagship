# C:\DevProjects\risk_analysis_flagship\fraud_detection_system\reports\utils\fraud_report_utils.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import json
import math
import statistics
import datetime as dt

import pandas as pd
import numpy as np

def resolve_paths(repo_root: Path, report_date: dt.date) -> Dict[str, Path]:
    ymd = report_date.strftime("%Y%m%d")
    ymd_dash = report_date.strftime("%Y-%m-%d")
    out_dir = repo_root / "docs_global" / "reports" / "fraud" / ymd_dash
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "logs_jsonl": repo_root / "fraud_detection_system" / "api" / "logs" / f"{ymd}.jsonl",
        "monitor_dir": repo_root / "docs_global" / "monitoring" / "fraud" / ymd_dash,
        "out_dir": out_dir,
        "kpis_json": out_dir / "kpis.json",
        "html_out": out_dir / "fraud_daily_report.html",
        "template_ipynb": repo_root / "fraud_detection_system" / "reports" / "templates" / "fraud_daily_report.ipynb",
    }

def load_jsonl_safe(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                # skip bad lines but continue
                continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)

    # Normalize expected fields
    if "rules_hit" in df.columns:
        df["rules_hit"] = df["rules_hit"].apply(lambda x: x if isinstance(x, list) else ([] if pd.isna(x) else [x]))
        df["rules_count"] = df["rules_hit"].apply(lambda xs: len(xs))
    else:
        df["rules_hit"] = [[] for _ in range(len(df))]
        df["rules_count"] = 0

    if "latency_ms" not in df.columns:
        df["latency_ms"] = np.nan

    if "decision" not in df.columns:
        df["decision"] = "allow"

    for col in ["proba", "model_ts", "arm", "label", "country", "device_id"]:
        if col not in df.columns:
            df[col] = np.nan

    return df

def load_monitor_artifacts(monitor_dir: Path) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    drift_csv = monitor_dir / "drift_summary.csv"
    metrics_json = monitor_dir / "metrics.json"
    # Safe CSV read: skip if missing or empty; catch parser errors
    drift_df = pd.DataFrame()
    if drift_csv.exists() and drift_csv.stat().st_size > 0:
        try:
            drift_df = pd.read_csv(drift_csv)
        except Exception:
            drift_df = pd.DataFrame()
    # Safe JSON read: skip if missing or blank; catch JSON errors
    metrics: Dict[str, Any] = {}
    if metrics_json.exists() and metrics_json.stat().st_size > 0:
        try:
            txt = metrics_json.read_text(encoding="utf-8").strip()
            metrics = json.loads(txt) if txt else {}
        except Exception:
            metrics = {}
    return drift_df, metrics

def _nan_to_none(x: Any) -> Optional[float]:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
    except Exception:
        pass
    return x

def compute_kpis(
    df: pd.DataFrame,
    drift_metrics: Dict[str, Any] | None = None,
    per_fraud_usd: float = 200.0
) -> Dict[str, Any]:
    total_txns = int(len(df)) if len(df) else 0
    flagged_mask = pd.Series([False] * total_txns)
    if total_txns:
        flagged_mask = (
            df["decision"].astype(str).isin(["block", "review", "manual_review"])
            | (df["rules_count"].fillna(0) > 0)
        )

    flagged = int(flagged_mask.sum()) if total_txns else 0
    flagged_pct = (flagged / total_txns) if total_txns else 0.0

    lat = df["latency_ms"].dropna().astype(float) if total_txns else pd.Series([], dtype=float)
    p95_latency = float(np.percentile(lat, 95)) if len(lat) else None
    p50_latency = float(np.percentile(lat, 50)) if len(lat) else None

    precision = recall = fpr = None
    if total_txns and "label" in df.columns and df["label"].notna().any():
        y_true = df["label"].fillna(0).astype(int)
        y_pred = flagged_mask.astype(int)
        tp = int(((y_true == 1) & (y_pred == 1)).sum())
        fp = int(((y_true == 0) & (y_pred == 1)).sum())
        fn = int(((y_true == 1) & (y_pred == 0)).sum())
        tn = int(((y_true == 0) & (y_pred == 0)).sum())
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else None
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else None
        fpr = (fp / (fp + tn)) if (fp + tn) > 0 else None

    fraud_prevented_usd = None
    if total_txns:
        if "label" in df.columns and df["label"].notna().any():
            fraud_prevented_usd = float(((flagged_mask) & (df["label"].fillna(0).astype(int) == 1)).sum() * per_fraud_usd)
        else:
            fraud_prevented_usd = float(flagged * per_fraud_usd)

    arms = None
    if total_txns and "arm" in df.columns and df["arm"].notna().any():
        arms = []
        for arm, g in df.groupby(df["arm"].fillna("unknown")):
            n = int(len(g))
            fm = (
                g["decision"].astype(str).isin(["block", "review", "manual_review"])
                | (g["rules_count"].fillna(0) > 0)
            )
            arms.append({
                "arm": str(arm),
                "n": n,
                "flagged": int(fm.sum()),
                "flagged_pct": float((fm.sum()/n) if n else 0.0)
            })

    rules_counter = {}
    if total_txns and "rules_hit" in df.columns:
        for xs in df["rules_hit"]:
            if isinstance(xs, list):
                for r in xs:
                    rules_counter[r] = rules_counter.get(r, 0) + 1

    kpis = {
        "total_txns": total_txns,
        "flagged": flagged,
        "flagged_pct": flagged_pct,
        "p50_latency_ms": _nan_to_none(p50_latency),
        "p95_latency_ms": _nan_to_none(p95_latency),
        "precision": _nan_to_none(precision),
        "recall": _nan_to_none(recall),
        "fpr": _nan_to_none(fpr),
        "fraud_prevented_usd": _nan_to_none(fraud_prevented_usd),
        "arms": arms,
        "rules_top": sorted([{"rule": k, "count": v} for k, v in rules_counter.items()],
                            key=lambda d: d["count"], reverse=True)[:20],
        "drift_metrics_present": bool(drift_metrics),
    }
    return kpis

def save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def render_nb_or_fallback(template_ipynb: Path, work_dir: Path, html_out: Path) -> str:
    """
    Try to execute the notebook and export HTML.
    If anything fails (nbconvert not installed, kernel missing, etc.), render a minimal HTML fallback.
    Returns: "nbconvert" or "fallback:<reason>"
    """
    try:
        import platform, asyncio, uuid
        import nbformat as nbf
        from nbconvert.preprocessors import ExecutePreprocessor
        from nbconvert import HTMLExporter

        # Windows: use selector loop to avoid ZMQ warning
        if platform.system() == "Windows":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                pass

        nb = nbf.read(str(template_ipynb), as_version=4)
        # Ensure every cell has an 'id' to avoid MissingIDFieldWarning
        for cell in nb.get("cells", []):
            if "id" not in cell:
                cell["id"] = uuid.uuid4().hex

        ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
        ep.preprocess(nb, {"metadata": {"path": str(work_dir)}})

        html_exporter = HTMLExporter()
        body, _ = html_exporter.from_notebook_node(nb)
        html_out.write_text(body, encoding="utf-8")
        return "nbconvert"
    except Exception as e:
        # Fallback: read kpis.json and build a very simple HTML summary
        kpis_path = work_dir / "kpis.json"
        try:
            data = json.loads(kpis_path.read_text(encoding="utf-8")) if kpis_path.exists() else {}
        except Exception:
            data = {}
        parts = [
            "<!doctype html><html><head><meta charset='utf-8'><title>Fraud Daily Report (Fallback)</title>",
            "<style>body{font-family:Segoe UI,Arial;margin:24px;} h1{margin:0 0 12px} table{border-collapse:collapse} td,th{border:1px solid #ddd;padding:6px 10px}</style>",
            "</head><body>",
            "<h1>Fraud Daily Report (Fallback)</h1>",
            "<h3>Executive Snapshot</h3>",
            "<table>",
        ]
        for k in ["total_txns","flagged","flagged_pct","p50_latency_ms","p95_latency_ms","precision","recall","fpr","fraud_prevented_usd"]:
            parts.append(f"<tr><th>{k}</th><td>{data.get(k,'')}</td></tr>")
        parts.append("</table>")
        if data.get("arms"):
            parts.append("<h3>A/B Arms</h3><table><tr><th>arm</th><th>n</th><th>flagged</th><th>flagged_pct</th></tr>")
            for a in data["arms"]:
                parts.append(f"<tr><td>{a['arm']}</td><td>{a['n']}</td><td>{a['flagged']}</td><td>{a['flagged_pct']}</td></tr>")
            parts.append("</table>")
        if data.get("rules_top"):
            parts.append("<h3>Top Rules</h3><table><tr><th>rule</th><th>count</th></tr>")
            for r in data["rules_top"]:
                parts.append(f"<tr><td>{r['rule']}</td><td>{r['count']}</td></tr>")
            parts.append("</table>")
        parts.append(f"<p style='color:#888'>Rendered via fallback because nbconvert failed: {e}</p>")
        parts.append("</body></html>")
        html_out.write_text("".join(parts), encoding="utf-8")
        return f"fallback:{e}"
