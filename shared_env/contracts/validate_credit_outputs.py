# C:\DevProjects\risk_analysis_flagship\shared_env\contracts\validate_credit_outputs.py
from pathlib import Path
import sys, re
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCORING_DIR = ROOT / "credit_scoring_system" / "outputs" / "scoring"

# Accept both PD and pd (and a few common aliases)
PD_CANDIDATES = ["PD","pd","prob_default","pd_hat","prediction","pred","score_pd"]
ID_CANDIDATES = ["borrower_id","loan_id","customer_id","account_id","id"]
# If a date column is missing, we will infer it from the filename (YYYYMMDD in stem)
DATE_CANDIDATES = ["as_of_date","date","run_date","scored_date","business_date"]

def _files(pattern): return sorted(SCORING_DIR.glob(pattern))

def _read_any(p: Path) -> pd.DataFrame:
    return pd.read_parquet(p) if p.suffix.lower()==".parquet" else pd.read_csv(p)

def _pick(cands, cols):
    low = {c.lower(): c for c in cols}
    for n in cands:
        if n.lower() in low: return low[n.lower()]
    return None

def _infer_date_from_name(p: Path) -> str | None:
    # match YYYYMMDD anywhere in stem (e.g., pd_scores_20251023)
    m = re.search(r"(\d{8})", p.stem)
    return m.group(1) if m else None

def validate_pd_scores(p: Path):
    df = _read_any(p)

    pid = _pick(ID_CANDIDATES, df.columns)
    ppd = _pick(PD_CANDIDATES, df.columns)
    pdt = _pick(DATE_CANDIDATES, df.columns)

    missing = []
    if not pid: missing.append("borrower_id (any of: " + ", ".join(ID_CANDIDATES) + ")")
    if not ppd: missing.append("PD (any of: " + ", ".join(PD_CANDIDATES) + ")")
    if missing:
        raise AssertionError(f"{p.name}: missing {missing}. cols={list(df.columns)}")

    # If no date column, derive from filename (tolerant contract for Stage 8)
    if not pdt:
        inferred = _infer_date_from_name(p)
        if inferred:
            pdt = "as_of_date"
            df[pdt] = inferred
        else:
            raise AssertionError(f"{p.name}: no date column and cannot infer date from filename")

    s = pd.to_numeric(df[ppd], errors="coerce")
    if s.isna().any():
        raise AssertionError(f"{p.name}: PD column contains non-numeric values")
    if not ((s >= 0).all() and (s <= 1).all()):
        raise AssertionError(f"{p.name}: PD must be within [0,1]")

    print(f"[OK] PD scores contract: {p.name}  (ID={pid}, PD={ppd}, DATE={pdt})")

def validate_rollups(p: Path):
    df = _read_any(p)
    required = {"grade","state","vintage_year","borrowers","avg_PD","total_EL"}
    if not required.issubset(df.columns):
        missing = sorted(required - set(df.columns))
        raise AssertionError(f"{p.name}: rollup missing {missing}. cols={list(df.columns)}")
    s = pd.to_numeric(df["avg_PD"], errors="coerce")
    if s.isna().any() or not ((s>=0).all() and (s<=1).all()):
        raise AssertionError(f"{p.name}: avg_PD must be in [0,1]")
    print(f"[OK] Segment rollups contract: {p.name}")

def main():
    if not SCORING_DIR.exists():
        print("[WARN] scoring dir missing; skipping")
        return 0

    # Prefer per-borrower PD scores (daily), else accept segment rollups (derived)
    pd_files = _files("pd_scores_*.parquet") + _files("pd_scores_*.csv")
    if pd_files:
        validate_pd_scores(pd_files[-1]); return 0

    roll = _files("segment_rollups_*.parquet") + _files("segment_rollups_*.csv")
    if roll:
        validate_rollups(roll[-1]); return 0

    print("[WARN] No scoring outputs found (pd_scores_* or segment_rollups_*)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
