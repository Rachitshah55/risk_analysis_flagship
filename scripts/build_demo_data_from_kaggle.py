import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd


# ----------------- PATHS -----------------
ROOT = Path(__file__).resolve().parents[1]

CREDIT_SRC = ROOT / "data" / "kaggle" / "credit" / "cs-training.csv"
FRAUD_SRC = ROOT / "data" / "kaggle" / "fraud" / "fraudTrain.csv"

OUT_CREDIT = ROOT / "docs_site" / "demo_data" / "credit"
OUT_FRAUD = ROOT / "docs_site" / "demo_data" / "fraud"

OUT_CREDIT.mkdir(parents=True, exist_ok=True)
OUT_FRAUD.mkdir(parents=True, exist_ok=True)


# ----------------- HELPERS -----------------
def last_n_dates(n_days: int):
    today = dt.date.today()
    return [(today - dt.timedelta(days=i)) for i in range(n_days - 1, -1, -1)]


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ----------------- CREDIT (Give Me Some Credit) -----------------
def build_credit_series(n_days: int = 30):
    if not CREDIT_SRC.exists():
        raise FileNotFoundError(f"Credit CSV not found: {CREDIT_SRC}")

    df = pd.read_csv(CREDIT_SRC)

    if "SeriousDlqin2yrs" not in df.columns:
        raise ValueError(
            "Expected 'SeriousDlqin2yrs' column in credit dataset "
            f"columns={list(df.columns)}"
        )

    base_pd = float(df["SeriousDlqin2yrs"].mean())  # ~0.067
    # Use median monthly income as a rough portfolio scale
    if "MonthlyIncome" in df.columns:
        base_income = float(df["MonthlyIncome"].dropna().median())
    else:
        base_income = 6000.0

    # Scale EL so numbers look realistic but not insane
    base_el = base_income * 20  # arbitrary but stable

    rng = np.random.default_rng(42)
    dates = last_n_dates(n_days)

    rows = []
    approvals_base = 150
    rejections_base = 50

    for d in dates:
        pd_today = clamp(
            base_pd + rng.normal(0, 0.005),  # ±0.5 percentage point
            0.03,
            0.15,
        )
        el_today = int(base_el * (1 + rng.normal(0, 0.08)))

        approvals = int(
            approvals_base * (1 + rng.normal(0, 0.05))
        )
        approvals = max(80, approvals)

        rejections = int(
            rejections_base * (1 + rng.normal(0, 0.10))
        )
        rejections = max(20, rejections)

        rows.append(
            [
                d.isoformat(),
                f"{pd_today:.3f}",
                el_today,
                approvals,
                rejections,
            ]
        )

    out_path = OUT_CREDIT / "kpis_daily.csv"
    pd.DataFrame(
        rows,
        columns=["date", "avg_pd", "el_today", "approvals", "rejections"],
    ).to_csv(out_path, index=False)
    print(f"[OK] Wrote credit KPIs → {out_path}")


# ----------------- FRAUD (Transactions Fraud Detection) -----------------
def build_fraud_series(n_days: int = 30):
    if not FRAUD_SRC.exists():
        raise FileNotFoundError(f"Fraud CSV not found: {FRAUD_SRC}")

    df = pd.read_csv(FRAUD_SRC)

    # Label column is is_fraud in this dataset
    label_col_candidates = ["is_fraud", "isFraud", "fraud", "Class"]
    label_col = next(
        (c for c in label_col_candidates if c in df.columns),
        None,
    )
    if label_col is None:
        raise ValueError(
            f"Could not find fraud label column in {FRAUD_SRC}; "
            f"columns={list(df.columns)}"
        )

    fraud_rate = float(df[label_col].mean())  # ~1–2%

    # Base flagged rate: detection model flags ~3–4% of transactions
    base_flagged = clamp(fraud_rate * 3.0, 0.02, 0.05)

    rng = np.random.default_rng(99)
    dates = last_n_dates(n_days)

    kpi_rows = []
    metrics_rows = []

    precision = 0.84
    recall = 0.61

    for d in dates:
        flagged = clamp(base_flagged + rng.normal(0, 0.0015), 0.02, 0.05)
        precision = clamp(precision + rng.normal(0, 0.004), 0.80, 0.88)
        recall = clamp(recall + rng.normal(0, 0.004), 0.55, 0.72)

        kpi_rows.append(
            [
                d.isoformat(),
                f"{flagged:.3f}",
                f"{precision:.3f}",
                f"{recall:.3f}",
            ]
        )
        metrics_rows.append(
            [
                d.isoformat(),
                f"{precision:.3f}",
                f"{recall:.3f}",
            ]
        )

    kpi_path = OUT_FRAUD / "kpis_daily.csv"
    metrics_path = OUT_FRAUD / "metrics_daily.csv"

    pd.DataFrame(
        kpi_rows,
        columns=["date", "flagged_rate", "precision", "recall"],
    ).to_csv(kpi_path, index=False)

    pd.DataFrame(
        metrics_rows,
        columns=["date", "precision", "recall"],
    ).to_csv(metrics_path, index=False)

    print(f"[OK] Wrote fraud KPIs   → {kpi_path}")
    print(f"[OK] Wrote fraud metrics→ {metrics_path}")


# ----------------- MAIN -----------------
if __name__ == "__main__":
    print("[INFO] Building demo CSVs from Kaggle snapshots...")
    build_credit_series(n_days=30)
    build_fraud_series(n_days=30)
    print("[DONE] Demo data under docs_site/demo_data/*")
