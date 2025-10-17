from pathlib import Path
import json, uuid

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "fraud_detection_system" / "reports" / "templates" / "fraud_daily_report.ipynb"
OUT.parent.mkdir(parents=True, exist_ok=True)

def md(text: str):
    return {"cell_type":"markdown","metadata":{},"source": text, "id": uuid.uuid4().hex}

def code(lines):
    # Ensure each code cell is a SINGLE string with real newlines
    if isinstance(lines, (list, tuple)):
        src = "\n".join(lines) + "\n"
    else:
        src = str(lines) + ("\n" if not str(lines).endswith("\n") else "")
    return {"cell_type":"code","metadata":{},"source": src, "id": uuid.uuid4().hex}

cells = [
    md("# Fraud — Daily Ops Report"),
    code([
        "from pathlib import Path",
        "import json",
        "import pandas as pd",
        "from datetime import datetime",
        "try:",
        "    import matplotlib.pyplot as plt",
        "    HAS_MPL = True",
        "except Exception:",
        "    HAS_MPL = False",
        "",
        "# Working dir is .../docs_global/reports/fraud/YYYY-MM-DD (runner sets it)",
        "WORKDIR = Path.cwd()",
        "PROJECT_ROOT = WORKDIR.parents[4]     # YYYY-MM-DD→fraud→reports→docs_global→REPO_ROOT",
        "REPORT_DATE = WORKDIR.name            # YYYY-MM-DD",
        "",
        "# KPIs",
        "kpis = {}",
        "kpath = WORKDIR / 'kpis.json'",
        "if kpath.exists():",
        "    kpis = json.loads(kpath.read_text(encoding='utf-8'))",
        "",
        "# Drift artifacts (safe read)",
        "drift_dir = WORKDIR.parents[2] / 'monitoring' / 'fraud' / REPORT_DATE",
        "drift_csv = drift_dir / 'drift_summary.csv'",
        "drift_df = pd.DataFrame()",
        "if drift_csv.exists() and drift_csv.stat().st_size > 0:",
        "    try:",
        "        drift_df = pd.read_csv(drift_csv)",
        "    except Exception:",
        "        drift_df = pd.DataFrame()",
        "metrics_json = drift_dir / 'metrics.json'",
        "try:",
        "    mon_metrics = json.loads(metrics_json.read_text(encoding='utf-8')) if metrics_json.exists() and metrics_json.stat().st_size>0 else {}",
        "except Exception:",
        "    mon_metrics = {}",
        "",
        "# Raw logs (optional)",
        "logs_path = (PROJECT_ROOT / 'fraud_detection_system' / 'api' / 'logs' / REPORT_DATE.replace('-','')).with_suffix('.jsonl')",
        "rows = []",
        "if logs_path.exists():",
        "    for line in logs_path.read_text(encoding='utf-8').splitlines():",
        "        line=line.strip()",
        "        if not line:",
        "            continue",
        "        try:",
        "            rows.append(json.loads(line))",
        "        except Exception:",
        "            pass",
        "",
        "df = pd.DataFrame(rows)",
        "if 'rules_hit' in df.columns:",
        "    df['rules_count'] = df['rules_hit'].apply(lambda x: len(x) if isinstance(x, list) else 0)",
        "else:",
        "    df['rules_count'] = 0",
        "",
        "df.head(3)",
    ]),
    md("## 1) Executive Snapshot"),
    code([
        "snap = {k: kpis.get(k) for k in ['total_txns','flagged','flagged_pct','p50_latency_ms','p95_latency_ms','precision','recall','fpr','fraud_prevented_usd']}",
        "pd.DataFrame([snap])",
    ]),
    md("## 2) Model Performance (labels permitting) + A/B (if present)"),
    code([
        "arms = kpis.get('arms') or []",
        "pd.DataFrame(arms) if arms else pd.DataFrame({'info':['No A/B arms present today']})",
    ]),
    md("## 3) Drift & Ops"),
    code("drift_df.head(10) if len(drift_df) else pd.DataFrame({'info':['No drift_summary.csv found or empty']})"),
    code([
        "if HAS_MPL and 'latency_ms' in df.columns and df['latency_ms'].notna().any():",
        "    plt.figure()",
        "    plt.hist(df['latency_ms'].dropna().astype(float), bins=30)",
        "    plt.title('Latency (ms) — Distribution')",
        "    plt.xlabel('latency_ms')",
        "    plt.ylabel('count')",
        "    plt.show()",
        "else:",
        "    pd.DataFrame({'info':['No latency data or matplotlib unavailable']})",
    ]),
    md("## 4) Governance Appendix"),
    code([
        "from collections import Counter",
        "ctr = Counter()",
        "if 'rules_hit' in df.columns:",
        "    for xs in df['rules_hit']:",
        "        if isinstance(xs, list): ctr.update(xs)",
        "top_rules = pd.DataFrame([{'rule':k,'count':v} for k,v in ctr.most_common(20)])",
        "top_rules if len(top_rules) else pd.DataFrame({'info':['No rules_hit data present']})",
    ]),
]

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name":"Python 3", "language":"python", "name":"python3"},
        "language_info": {"name":"python"}
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

OUT.write_text(json.dumps(nb, indent=2), encoding="utf-8")
print(f"[OK] Wrote notebook template → {OUT}")
