# ===== BEGIN: health_checks_stage5.py =====
from pathlib import Path
from datetime import datetime
import sys

root = Path(r"C:\DevProjects\risk_analysis_flagship")

today_str  = datetime.now().strftime("%Y-%m-%d")
month_str  = datetime.now().strftime("%Y-%m")

# Preferred (daily) locations
credit_daily = root / f"docs_global/monitoring/credit/{today_str}"
fraud_daily  = root / f"docs_global/monitoring/fraud/{today_str}"

# Legacy (monthly) credit fallback for backward compatibility
credit_month = root / f"docs_global/monitoring/credit/{month_str}"

problems = []
infos    = []

# --- Credit check: prefer daily; fallback to monthly if present ---
if credit_daily.exists():
    if not (credit_daily / "drift_summary.csv").exists():
        problems.append(f"Credit: drift_summary.csv not found in {credit_daily}")
else:
    if credit_month.exists():
        if (credit_month / "drift_summary.csv").exists():
            infos.append(f"Credit: using legacy monthly folder {credit_month} (consider switching to daily only)")
        else:
            problems.append(f"Credit: drift_summary.csv not found in {credit_month}")
    else:
        problems.append(f"Missing credit monitoring folder: {credit_daily} (and legacy {credit_month})")

# --- Fraud check: daily ---
if fraud_daily.exists():
    if not (fraud_daily / "metrics.json").exists():
        problems.append(f"Fraud: metrics.json not found in {fraud_daily}")
else:
    problems.append(f"Missing fraud monitoring folder: {fraud_daily}")

# --- Result ---
if problems:
    print("❌ STAGE 5 HEALTH CHECKS FAILED")
    for p in problems:
        print(" -", p)
    if infos:
        print("\nINFO:")
        for i in infos:
            print(" -", i)
    sys.exit(1)
else:
    print("✅ STAGE 5 HEALTH CHECKS PASSED")
    for i in infos:
        print("ℹ️", i)
# ===== END: health_checks_stage5.py =====
