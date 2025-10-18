# C:\DevProjects\risk_analysis_flagship\fraud_detection_system\reports\rollup_month_fraud_reports.py
from __future__ import annotations
from pathlib import Path
import argparse, json, re, os
from datetime import date, datetime
from collections import defaultdict, Counter
from typing import Dict, Any, List

import mlflow

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../fraud_detection_system/reports → REPO
REPORTS_ROOT = REPO_ROOT / "docs_global" / "reports" / "fraud"

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--month", help="YYYY-MM (default: this month)", default=None)
    return p.parse_args()

def current_month() -> str:
    return date.today().strftime("%Y-%m")

def ensure_month_str(s: str | None) -> str:
    if not s:
        return current_month()
    if not MONTH_DIR_RE.match(s):
        raise SystemExit(f"--month must be YYYY-MM (got {s})")
    return s

def find_daily_dirs(month_str: str) -> List[Path]:
    # daily dirs live one level under REPORTS_ROOT, named YYYY-MM-DD; filter by prefix
    if not REPORTS_ROOT.exists():
        return []
    wanted_prefix = f"{month_str}-"
    out = []
    for p in REPORTS_ROOT.iterdir():
        if p.is_dir() and DATE_DIR_RE.match(p.name) and p.name.startswith(wanted_prefix):
            out.append(p)
    return sorted(out)

def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        txt = path.read_text(encoding="utf-8").strip()
        return json.loads(txt) if txt else {}
    except Exception:
        return {}

def weighted_avg(pairs: List[tuple[float, float]]) -> float | None:
    # pairs: [(value, weight), ...]
    num = 0.0
    den = 0.0
    for v, w in pairs:
        if v is None:  # skip missing
            continue
        try:
            vv = float(v); ww = float(w)
        except Exception:
            continue
        num += vv * ww
        den += ww
    return (num / den) if den > 0 else None

def aggregate_month(month_str: str) -> Dict[str, Any]:
    day_dirs = find_daily_dirs(month_str)
    days_total = len(day_dirs)
    days_with_kpis = 0

    total_txns = 0
    flagged = 0
    p50_pairs, p95_pairs = [], []
    precision_pairs, recall_pairs, fpr_pairs = [], [], []

    # arms aggregation
    arms_ctr = defaultdict(lambda: {"n": 0, "flagged": 0})
    # rules aggregation
    rules_ctr = Counter()

    # collect day list for appendix
    day_list = []

    for d in day_dirs:
        kpath = d / "kpis.json"
        k = load_json(kpath)
        if not k:
            continue
        days_with_kpis += 1
        day_list.append({"date": d.name, "kpis_present": True, "folder": str(d)})

        n = int(k.get("total_txns") or 0)
        f = int(k.get("flagged") or 0)
        total_txns += n
        flagged += f

        p50_pairs.append((k.get("p50_latency_ms"), n))
        p95_pairs.append((k.get("p95_latency_ms"), n))

        # NB: precision/recall/fpr are averaged by total volume (approx)
        if k.get("precision") is not None:
            precision_pairs.append((k.get("precision"), n))
        if k.get("recall") is not None:
            recall_pairs.append((k.get("recall"), n))
        if k.get("fpr") is not None:
            fpr_pairs.append((k.get("fpr"), n))

        # A/B arms (sum n and flagged; recompute pct later)
        if k.get("arms"):
            for a in k["arms"]:
                arm = str(a.get("arm", "unknown"))
                arms_ctr[arm]["n"] += int(a.get("n") or 0)
                arms_ctr[arm]["flagged"] += int(a.get("flagged") or 0)

        # Rules top (sum counts across days)
        if k.get("rules_top"):
            for r in k["rules_top"]:
                rules_ctr[str(r.get("rule"))] += int(r.get("count") or 0)

    flagged_pct = (flagged / total_txns) if total_txns else 0.0
    p50 = weighted_avg(p50_pairs)
    p95 = weighted_avg(p95_pairs)
    prec = weighted_avg(precision_pairs)
    rec = weighted_avg(recall_pairs)
    fpr = weighted_avg(fpr_pairs)

    # Compile arms table
    arms = []
    for arm, vals in sorted(arms_ctr.items(), key=lambda kv: kv[0]):
        n = int(vals["n"]); f = int(vals["flagged"])
        arms.append({"arm": arm, "n": n, "flagged": f, "flagged_pct": (f/n if n else 0.0)})

    # Rules top 30 for the month
    rules_top = [{"rule": r, "count": c} for r, c in rules_ctr.most_common(30)]

    out = {
        "month": month_str,
        "days_total": days_total,
        "days_with_kpis": days_with_kpis,
        "total_txns": total_txns,
        "flagged": flagged,
        "flagged_pct": flagged_pct,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "precision": prec,
        "recall": rec,
        "fpr": fpr,
        "arms": arms,
        "rules_top": rules_top,
        "days": day_list,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    return out

def write_month_outputs(month_str: str, summary: Dict[str, Any]) -> Path:
    month_dir = REPORTS_ROOT / month_str
    month_dir.mkdir(parents=True, exist_ok=True)
    json_path = month_dir / "monthly_kpis.json"
    html_path = month_dir / "fraud_monthly_summary.html"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # simple HTML render
    def tr(k, v):
        return f"<tr><th>{k}</th><td>{'' if v is None else v}</td></tr>"
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>Fraud Monthly Summary</title>",
        "<style>body{font-family:Segoe UI,Arial;margin:24px;} h1{margin:0 0 6px} h2{margin:18px 0 6px} table{border-collapse:collapse;margin:6px 0} th,td{border:1px solid #ddd;padding:6px 10px} .muted{color:#777}</style>",
        "</head><body>",
        f"<h1>Fraud — Monthly Summary ({month_str})</h1>",
        "<h2>Executive Snapshot</h2><table>",
        tr("total_txns", summary["total_txns"]),
        tr("flagged", summary["flagged"]),
        tr("flagged_pct", round(summary["flagged_pct"], 4) if summary["total_txns"] else 0.0),
        tr("p50_latency_ms", None if summary['p50_latency_ms'] is None else round(summary['p50_latency_ms'], 2)),
        tr("p95_latency_ms", None if summary['p95_latency_ms'] is None else round(summary['p95_latency_ms'], 2)),
        tr("precision", None if summary['precision'] is None else round(summary['precision'], 4)),
        tr("recall", None if summary['recall'] is None else round(summary['recall'], 4)),
        tr("fpr", None if summary['fpr'] is None else round(summary['fpr'], 4)),
        tr("days_with_kpis", f"{summary['days_with_kpis']} / {summary['days_total']}"),
        "</table>",
    ]

    # Arms
    parts += ["<h2>A/B Arms (month)</h2>"]
    if summary["arms"]:
        parts += ["<table><tr><th>arm</th><th>n</th><th>flagged</th><th>flagged_pct</th></tr>"]
        for a in summary["arms"]:
            parts += [f"<tr><td>{a['arm']}</td><td>{a['n']}</td><td>{a['flagged']}</td><td>{round(a['flagged_pct'],4)}</td></tr>"]
        parts += ["</table>"]
    else:
        parts += ["<p class='muted'>No A/B arm data present this month.</p>"]

    # Rules
    parts += ["<h2>Top Rules (month)</h2>"]
    if summary["rules_top"]:
        parts += ["<table><tr><th>rule</th><th>count</th></tr>"]
        for r in summary["rules_top"]:
            parts += [f"<tr><td>{r['rule']}</td><td>{r['count']}</td></tr>"]
        parts += ["</table>"]
    else:
        parts += ["<p class='muted'>No rules_hit data present this month.</p>"]

    # Days appendix
    parts += ["<h2>Days Covered</h2>"]
    if summary["days"]:
        parts += ["<table><tr><th>date</th><th>kpis_present</th></tr>"]
        for d in summary["days"]:
            parts += [f"<tr><td>{d['date']}</td><td>{'yes' if d['kpis_present'] else 'no'}</td></tr>"]
        parts += ["</table>"]
    else:
        parts += ["<p class='muted'>No day folders found for this month.</p>"]

    parts += ["</body></html>"]
    html_path.write_text("".join(parts), encoding="utf-8")

    return month_dir

def log_mlflow(summary_dir: Path, summary: Dict[str, Any]):
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", f"file:///{(REPO_ROOT/'mlruns').as_posix()}")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("fraud_stage7_monthly_rollup")

    with mlflow.start_run(run_name=f"fraud_monthly_{summary['month'].replace('-','')}"):
        # Metrics
        for k in ["total_txns","flagged","flagged_pct","p50_latency_ms","p95_latency_ms","precision","recall","fpr","days_with_kpis","days_total"]:
            v = summary.get(k)
            if isinstance(v, (int, float)) and v is not None:
                mlflow.log_metric(k, float(v))
        # Params for context
        mlflow.log_param("month", summary["month"])
        mlflow.log_param("arms_count", str(len(summary.get("arms", []))))
        mlflow.log_param("rules_top_count", str(len(summary.get("rules_top", []))))
        # Artifacts
        html = summary_dir / "fraud_monthly_summary.html"
        jsonp = summary_dir / "monthly_kpis.json"
        if html.exists():
            mlflow.log_artifact(str(html), artifact_path="report")
        if jsonp.exists():
            mlflow.log_artifact(str(jsonp), artifact_path="report")

def main():
    args = parse_args()
    month_str = ensure_month_str(args.month)

    summary = aggregate_month(month_str)
    out_dir = write_month_outputs(month_str, summary)
    log_mlflow(out_dir, summary)

    print(f"[OK] Fraud monthly summary written to: {out_dir/'fraud_monthly_summary.html'}")
    print(f"[OK] KPIs saved to: {out_dir/'monthly_kpis.json'}")

if __name__ == "__main__":
    main()
