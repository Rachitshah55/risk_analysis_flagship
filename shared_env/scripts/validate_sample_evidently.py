import os
import pandas as pd
import importlib

ROOT = r"C:\DevProjects\risk_analysis_flagship"
SRC  = os.path.join(ROOT, "data", "raw", "sample_loans.csv")
OUT_DIR = os.path.join(ROOT, "docs_global", "validation")
OUT_HTML = os.path.join(OUT_DIR, "sample_loans_quality.html")

os.makedirs(OUT_DIR, exist_ok=True)
df = pd.read_csv(SRC)

# Minimal sanity checks
assert "loan_amount" in df.columns, "loan_amount missing"
assert (df["loan_amount"] > 0).all(), "loan_amount must be > 0"

def try_evidently_report(df):
    """Try to build an Evidently HTML report with whatever 0.7.x exposes.
    Return True if written, False otherwise.
    """
    try:
        # Report import (0.7.x)
        try:
            Report = importlib.import_module("evidently.report").Report
        except Exception:
            Report = importlib.import_module("evidently").Report  # some builds expose at top level

        # Metrics module (0.7.x namespace)
        em = importlib.import_module("evidently.metrics")

        # Prefer a zero-arg metric/preset if available
        candidate_names = [
            "DataQualityPreset",       # often present
            "DatasetSummaryMetric",    # widely present in 0.7.x
        ]
        metric_cls = None
        for name in candidate_names:
            metric_cls = getattr(em, name, None)
            if metric_cls is not None:
                break

        if metric_cls is None:
            return False  # no compatible metric available

        metric = metric_cls()  # zero-arg metric
        report = Report(metrics=[metric])

        ref = df.head(3)  # tiny reference just to render
        report.run(reference_data=ref, current_data=df)
        report.save_html(OUT_HTML)
        return True
    except Exception:
        return False

used_evidently = try_evidently_report(df)

if not used_evidently:
    # Fallback: simple HTML summary so the step still succeeds
    html = [
        "<html><head><meta charset='utf-8'><title>Sample Loans – Quick Quality Summary</title></head><body>",
        "<h2>Sample Loans – Quick Quality Summary (Fallback)</h2>",
        "<p><em>Evidently metrics not available in this build; providing a basic data summary.</em></p>",
        "<h3>Head</h3>",
        df.head(10).to_html(index=False),
        "<h3>Describe</h3>",
        df.describe(include='all').to_html(),
        "</body></html>",
    ]
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

print(f"[OK] Wrote {OUT_HTML}")
