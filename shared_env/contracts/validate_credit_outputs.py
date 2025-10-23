from pathlib import Path
import sys, pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# Accept common variants and map to canonical names
PD_CANDIDATES = ["pd","prob_default","pd_hat","prediction","pred","score_pd"]
ID_CANDIDATES = ["borrower_id","loan_id","customer_id","account_id","id"]
DATE_CANDIDATES = ["as_of_date","date","run_date","scored_date","business_date"]

def _latest_scoring_file():
    out = ROOT / "credit_scoring_system" / "outputs" / "scoring"
    pats = ["*.parquet","*.csv"]
    files = []
    for p in pats:
        files += sorted(out.glob(p))
    return files[-1] if files else None

def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower()==".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)

def _pick(name_list, columns):
    cols_lower = {c.lower(): c for c in columns}
    for n in name_list:
        if n in cols_lower:
            return cols_lower[n]
    return None

def main():
    f = _latest_scoring_file()
    if not f:
        print("[WARN] No scoring output found under credit_scoring_system/outputs/scoring — skipping.")
        return 0
    df = _read_any(f)
    pid = _pick(ID_CANDIDATES, df.columns)
    ppd = _pick(PD_CANDIDATES, df.columns)
    pdt = _pick(DATE_CANDIDATES, df.columns)

    missing = []
    if not pid: missing.append("borrower_id (any of: "+", ".join(ID_CANDIDATES)+")")
    if not ppd: missing.append("pd (any of: "+", ".join(PD_CANDIDATES)+")")
    if not pdt: missing.append("as_of_date (any of: "+", ".join(DATE_CANDIDATES)+")")
    if missing:
        raise AssertionError(f"{f.name}: Missing required fields: {missing}. Columns present: {list(df.columns)}")

    # Basic range check
    pd_series = df[ppd].astype("float64")
    if not ((pd_series >= 0).all() and (pd_series <= 1).all()):
        raise AssertionError(f"{f.name}: PD must be within [0,1]")
    print(f"[OK] Credit outputs contract satisfied for {f.name} using columns: ID={pid}, PD={ppd}, DATE={pdt}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
