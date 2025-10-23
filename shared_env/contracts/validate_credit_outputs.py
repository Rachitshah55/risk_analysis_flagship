from pathlib import Path
import sys, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
def main():
    # Latest PD scores parquet (daily)
    out = ROOT / "credit_scoring_system" / "outputs" / "scoring"
    files = sorted(out.glob("pd_scores_*.parquet"))
    if not files:
        print("[WARN] No pd_scores_*.parquet found — skipping.")
        return 0
    df = pd.read_parquet(files[-1])
    required = {"borrower_id", "pd", "as_of_date"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise AssertionError(f"Missing required columns: {missing}")
    if not ((df["pd"] >= 0).all() and (df["pd"] <= 1).all()):
        raise AssertionError("PD must be within [0,1].")
    print("[OK] Credit outputs contract satisfied for", files[-1].name)
    return 0

if __name__ == "__main__":
    sys.exit(main())
