# Rebuilds credit_daily_report.ipynb with working cells and sys.path setup
from pathlib import Path
import nbformat as nbf

# ...\credit_scoring_system\reports\scaffold_credit_daily_notebook.py
# parents[0]=reports, [1]=credit_scoring_system, [2]=<project root>
ROOT = Path(__file__).resolve().parents[2]
NB_PATH = ROOT / "credit_scoring_system" / "reports" / "templates" / "credit_daily_report.ipynb"
NB_PATH.parent.mkdir(parents=True, exist_ok=True)

nb = nbf.v4.new_notebook()
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

nb.cells = [
    md("# Credit Daily Report\n\n**Sections:** Executive Summary • Drift Today • Calibration Today • Segments • Appendix"),
    # ── Sys.path bootstrap (so absolute imports work inside the notebook kernel)
    code(
        "import os, sys\n"
        "pr = os.environ.get('PROJECT_ROOT')\n"
        "if pr and pr not in sys.path:\n"
        "    sys.path.insert(0, pr)\n"
        "print('[Notebook] PROJECT_ROOT on sys.path:', pr in sys.path)\n"
        "DAY = os.environ.get('REPORT_DATE')\n"
        "print('[Notebook] REPORT_DATE =', DAY)\n"
    ),
    # ── Load utils & data for the day
    code(
        "from credit_scoring_system.reports.utils.credit_report_utils import load_daily, load_trailing, kpi_today_vs_trailing, el_by_segment\n"
        "today = load_daily(DAY)\n"
        "trail = load_trailing(7, DAY)\n"
        "kpis = kpi_today_vs_trailing(today, trail)\n"
        "kpis"
    ),
    md("## Executive Summary"),
    code("import pandas as pd\npd.DataFrame([kpis])"),
    md("## Drift Today"),
    code("df = today.get('drift_df')\ndisplay(df.head() if df is not None else 'No drift_summary.csv found for today.')"),
    md("## Calibration Today"),
    code("from IPython.display import Image, display\npng = today.get('calibration_png')\ndisplay(Image(filename=str(png))) if png else print('No calibration plot for today.')"),
    md("## Segments — Expected Loss by Segment"),
    code("seg = el_by_segment(DAY)\ndisplay(seg.head() if seg is not None else 'No segment rollups found for today.')"),
    md("## Appendix\n- Inputs: drift_summary.csv, calibration_plot.png\n- KPIs from optional pd_scores_YYYYMMDD.parquet and segment_rollups_YYYYMMDD.parquet."),
]

nbf.write(nb, NB_PATH)
print(f"[OK] Wrote {NB_PATH}")
