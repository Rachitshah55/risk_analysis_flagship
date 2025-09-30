# ===== BEGIN: health_checks_stage4_credit.py =====
from pathlib import Path
import glob, sys, time, os

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODELS_GLOB = str(ROOT / "credit_scoring_system" / "models" / "credit_*")
SCORES_DIR = ROOT / "credit_scoring_system" / "outputs" / "scoring"

def _latest(path_pattern: str) -> Path | None:
    cands = [Path(p) for p in glob.glob(path_pattern)]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None

def _latest_with_prefix(dir_path: Path, prefix: str) -> Path | None:
    cands = sorted(dir_path.glob(f"{prefix}_*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None

def _warn(msg: str):
    print(f"[WARN] {msg}")

def main():
    # 0) Folders exist
    assert (ROOT / "credit_scoring_system").exists(), "credit_scoring_system folder missing."
    assert (ROOT / "credit_scoring_system" / "outputs" / "scoring").exists(), "outputs/scoring folder missing."

    # 1) Model presence
    mdir = _latest(MODELS_GLOB)
    assert mdir and mdir.is_dir(), "No credit_* model directory found. Run Stage 3 training."
    ok_model = any((mdir / f).exists() for f in ["logreg_calibrated_or_plain.joblib", "xgb_model.joblib"])
    assert ok_model, f"Model files missing in {mdir}. Expect one of: logreg_calibrated_or_plain.joblib, xgb_model.joblib"

    # 2) Latest outputs (within 24h)
    now = time.time()
    pd_scores = _latest_with_prefix(SCORES_DIR, "pd_scores")
    segs = _latest_with_prefix(SCORES_DIR, "segment_rollups")
    assert pd_scores and segs, "Missing scoring outputs. Run score_credit_portfolio.py first."
    for p in (pd_scores, segs):
        age_h = (now - p.stat().st_mtime) / 3600.0
        assert age_h <= 24, f"Output {p.name} is older than 24h. Re-run scoring."

    # 3) Scores sanity
    df_scores = pd.read_parquet(pd_scores)
    assert len(df_scores) > 0, "pd_scores file has 0 rows."
    req_cols = {"borrower_id", "PD", "EAD", "LGD", "EL"}
    assert req_cols.issubset(df_scores.columns), f"pd_scores missing columns: {req_cols - set(df_scores.columns)}"
    assert (df_scores["EL"] >= 0).all(), "Found negative EL values in pd_scores."
    # Soft ranges
    if (df_scores["PD"] < 0).any() or (df_scores["PD"] > 1).any():
        _warn("PD contains values outside [0,1] (model/calibration issue?).")

    # 4) Segment rollups sanity
    df_seg = pd.read_parquet(segs)
    must_cols = {"borrowers", "total_EAD", "avg_PD", "total_EL"}
    assert must_cols.issubset(df_seg.columns), f"segment_rollups missing columns: {must_cols - set(df_seg.columns)}"
    assert (df_seg["total_EL"] >= 0).all(), "Found negative total_EL in segment rollups."
    # Optional: warn if any segment key column is missing or fully null
    segment_keys = [c for c in df_seg.columns if c not in {"borrowers", "total_EAD", "avg_PD", "total_EL"}]
    if not segment_keys:
        _warn("No segment keys detected in rollups (expected e.g., grade/state/vintage_year).")
    else:
        for k in segment_keys:
            if df_seg[k].isna().all():
                _warn(f"Segment key '{k}' is entirely null.")

    # 5) Optional SHAP artifact check (only if user enabled SHAP)
    if os.getenv("ENABLE_SHAP", "0") == "1":
        art = ROOT / "credit_scoring_system" / "models" / "artifacts_credit"
        if not art.exists():
            _warn("ENABLE_SHAP=1 but artifacts_credit/ directory not found (SHAP may have been skipped).")
        else:
            # Warn if no recent SHAP image
            pngs = list(art.glob("shap_summary_*.png"))
            if not pngs:
                _warn("ENABLE_SHAP=1 but no shap_summary_*.png found.")
            else:
                latest_png = max(pngs, key=lambda p: p.stat().st_mtime)
                if (now - latest_png.stat().st_mtime) / 3600.0 > 24:
                    _warn(f"Latest SHAP image {latest_png.name} is older than 24h.")

    print("✅ CREDIT STAGE 4 CHECKS PASSED")

if __name__ == "__main__":
    main()
# ===== END: health_checks_stage4_credit.py =====
