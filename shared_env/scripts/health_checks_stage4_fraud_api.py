# ===== BEGIN: health_checks_stage4_fraud_api.py =====
from pathlib import Path
import json
import sys
try:
    # Python 3.7+: force stdout/stderr to UTF-8 regardless of console code page
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fallback: strip characters not representable in the current code page
        print(msg.encode("ascii", "ignore").decode("ascii"))


ROOT = Path(__file__).resolve().parents[2]
FRAUD = ROOT / "fraud_detection_system"
MODELS = FRAUD / "models"
STREAM = FRAUD / "data" / "features_stream" / "stream_features.parquet"
RULES = FRAUD / "rules" / "rules_v1.yml"

def latest_model_dir():
    cands = [p for p in MODELS.glob("fraud_*") if p.is_dir()]
    if not cands:
        print("❌ No fraud_* model directories found."); sys.exit(1)
    return max(cands, key=lambda p: p.stat().st_mtime)

def main():
    mdir = latest_model_dir()
    need = [
        mdir / "xgb_model.joblib",
        mdir / "threshold.json",
        mdir / "feature_list.json",
        RULES,
        STREAM,
    ]
    missing = [str(p) for p in need if not p.exists()]
    if missing:
        print("❌ Missing artifacts:\n - " + "\n - ".join(missing)); sys.exit(1)

    thr = json.loads((mdir / "threshold.json").read_text(encoding="utf-8")).get("threshold", 0.5)
    if not (0.0 < float(thr) < 1.0):
        print(f"❌ threshold out of range: {thr}"); sys.exit(1)

    safe_print("✅ Stage 4 fraud API health checks passed.")

if __name__ == "__main__":
    main()
# ===== END: health_checks_stage4_fraud_api.py =====