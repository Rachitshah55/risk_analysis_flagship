import csv
import os
import zipfile
import subprocess
import datetime as dt
from pathlib import Path
from typing import List, Tuple


# ---------- CONFIG ----------
DATASET = os.environ.get(
    "KAGGLE_DATASET",
    "mohansacharya/credit-card-fraud-detection",  # you can swap this later
)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "docs_site" / "demo_data"
CREDIT_OUT = OUT_ROOT / "credit"
FRAUD_OUT = OUT_ROOT / "fraud"


# ---------- HELPERS ----------
def ensure_dirs() -> None:
    CREDIT_OUT.mkdir(parents=True, exist_ok=True)
    FRAUD_OUT.mkdir(parents=True, exist_ok=True)


def last_n_days(n: int) -> List[str]:
    today = dt.date.today()
    days = []
    for i in range(n):
        day = today - dt.timedelta(days=(n - 1 - i))
        days.append(day.isoformat())
    return days


def write_csv(path: Path, header: List[str], rows: List[List[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---------- KAGGLE DOWNLOAD (OPTIONAL) ----------
def try_download_dataset() -> int:
    """
    Best-effort download. Returns an approximate row-count to shape the synthetic series.
    If anything fails, returns a default row count.
    """
    print(f"[INFO] Attempting Kaggle download: {DATASET}")
    try:
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", DATASET, "-p", "."],
            check=True,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Kaggle download failed: {e}")
        return 100_000

    # Look for first ZIP in current dir
    zips = list(Path(".").glob("*.zip"))
    if not zips:
        print("[WARN] No .zip file found after Kaggle download. Using default row count.")
        return 100_000

    zpath = zips[0]
    try:
        with zipfile.ZipFile(zpath, "r") as zf:
            names = zf.namelist()
            csv_name = next((n for n in names if n.lower().endswith(".csv")), None)
            if csv_name is None:
                print("[WARN] No CSV inside Kaggle zip. Using default row count.")
                return 100_000

            with zf.open(csv_name) as f:
                # Count lines roughly (no parsing)
                count = sum(1 for _ in f)
                print(f"[INFO] Approx source row count: {count}")
                return max(count, 10_000)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Failed to inspect Kaggle zip: {e}")
        return 100_000


# ---------- SYNTHETIC SERIES ----------
def generate_series(row_factor: int) -> Tuple[List[List[object]], List[List[object]]]:
    """
    Build 30 days of synthetic KPIs shaped loosely by row_factor.
    Returns (credit_rows, fraud_rows).
    """
    import random

    rnd = random.Random(42)
    days = last_n_days(30)

    # Base scaling: more rows => bigger EL, more txns
    scale = max(1.0, min(row_factor / 100_000.0, 20.0))

    credit_rows: List[List[object]] = []
    avg_pd_base = 0.08
    el_base = 120_000 * scale
    approvals = int(150 * scale)
    rejections = int(50 * scale)

    for d in days:
        drift = (rnd.random() - 0.5) * 0.006  # +/- 0.3pp
        pd = max(0.04, min(0.12, avg_pd_base + drift))
        el_today = int(el_base * (1 + (rnd.random() - 0.5) * 0.1))
        a = max(50, int(approvals + (rnd.random() - 0.5) * 0.1 * approvals))
        r = max(10, int(rejections + (rnd.random() - 0.5) * 0.1 * rejections))
        credit_rows.append([d, f"{pd:.3f}", el_today, a, r])

    fraud_rows: List[List[object]] = []
    flagged_rate = 0.032
    precision = 0.840
    recall = 0.610

    for d in days:
        flagged_rate = max(0.02, min(0.05, flagged_rate + (rnd.random() - 0.5) * 0.002))
        precision = max(0.80, min(0.87, precision + (rnd.random() - 0.5) * 0.006))
        recall = max(0.55, min(0.70, recall + (rnd.random() - 0.5) * 0.006))
        fraud_rows.append(
            [d, f"{flagged_rate:.3f}", f"{precision:.3f}", f"{recall:.3f}"]
        )

    return credit_rows, fraud_rows


# ---------- MAIN PIPELINE ----------
def main() -> None:
    ensure_dirs()

    # Step 1: best-effort Kaggle download to shape counts
    row_factor = 100_000
    try:
        row_factor = try_download_dataset()
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] Kaggle step failed hard: {e} (using default row count)")

    # Step 2: always generate synthetic aggregates only
    credit_rows, fraud_rows = generate_series(row_factor)

    # Step 3: write CSVs into docs_site/demo_data/*
    write_csv(
        CREDIT_OUT / "kpis_daily.csv",
        ["date", "avg_pd", "el_today", "approvals", "rejections"],
        credit_rows,
    )

    write_csv(
        FRAUD_OUT / "kpis_daily.csv",
        ["date", "flagged_rate", "precision", "recall"],
        fraud_rows,
    )

    write_csv(
        FRAUD_OUT / "metrics_daily.csv",
        ["date", "precision", "recall"],
        [[r[0], r[2], r[3]] for r in fraud_rows],
    )

    print(f"[OK] Demo CSVs written under: {OUT_ROOT}")


if __name__ == "__main__":
    main()