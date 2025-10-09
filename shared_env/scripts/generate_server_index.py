# ===== BEGIN: generate_server_index.py =====
from __future__ import annotations
import json, urllib.request, urllib.error
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime

ROOT = Path(r"C:\DevProjects\risk_analysis_flagship")
IN_JSON = ROOT / r"docs_global\index_servers.json"
OUT_MD  = ROOT / r"docs_global\INDEX_SERVERS.md"
MLRUNS_URI = "file:///C:/DevProjects/risk_analysis_flagship/mlruns"

def http_up(url: str, timeout=2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False

def latest_run_links():
    out = {"credit": None, "fraud": None}
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        c = MlflowClient(tracking_uri=MLRUNS_URI)
        def last(exp_name):
            exp = c.get_experiment_by_name(exp_name)
            if not exp: return None
            runs = c.search_runs([exp.experiment_id], order_by=["attributes.start_time DESC"], max_results=1)
            if not runs: return None
            r = runs[0]
            return f"http://127.0.0.1:5000/#/experiments/{exp.experiment_id}/runs/{r.info.run_id}"
        out["credit"] = last("credit_stage5_monitoring")
        out["fraud"]  = last("fraud_stage5_monitoring")
    except Exception:
        pass
    return out

def main():
    if not IN_JSON.exists():
        raise SystemExit(f"[ERR] Missing {IN_JSON}. Run discover_endpoints.py first.")
    services = json.loads(IN_JSON.read_text(encoding="utf-8"))
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    links = latest_run_links()

    lines = []
    lines.append("# Local Services Index")
    lines.append("")
    lines.append(f"_Updated {ts}_")
    lines.append("")
    for s in services:
        base = s["base_url"]
        u = urlparse(base)
        port = u.port or (443 if u.scheme == "https" else 80)
        health = (base + s["health_path"]) if s.get("health_path") else base
        is_up = http_up(health)

        lines.append(f"## {s['name']}")
        lines.append(f"- Base: {base}")
        if s.get("docs_url"):   lines.append(f"- Docs: {base}{s['docs_url']}")
        if s.get("health_path"):lines.append(f"- Health: {health}")
        if s.get("start_label"):lines.append(f"- How to start: {s['start_label']} (port {port})")
        lines.append(f"- Status: {'UP' if is_up else 'DOWN'} (checked {ts})")
        lines.append("")

    if links["credit"] or links["fraud"]:
        lines.append("---")
        lines.append("### MLflow Latest Runs")
        if links["credit"]: lines.append(f"- Credit: {links['credit']}")
        if links["fraud"]:  lines.append(f"- Fraud: {links['fraud']}")
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Updated {OUT_MD}")

if __name__ == "__main__":
    main()
# ===== END: generate_server_index.py =====
