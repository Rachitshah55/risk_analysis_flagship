import json, os
from pathlib import Path

def test_credit_kpis_contract():
    # ensure kpis.json (if present) has required keys
    root = Path(__file__).resolve().parents[2]
    # look at latest credit daily KPIs if exists
    rpt_dir = root / "docs_global" / "reports" / "credit"
    if not rpt_dir.exists():
        return
    days = sorted([p for p in rpt_dir.iterdir() if p.is_dir()])
    if not days:
        return
    k = days[-1] / "kpis.json"
    if not k.exists():
        return
    data = json.loads(k.read_text(encoding="utf-8", errors="ignore"))
    # minimal shape check
    for key in ["avg_pd_today", "el_total_today"]:
        assert key in data
