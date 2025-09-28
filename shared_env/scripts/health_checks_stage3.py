# ===== BEGIN: health_checks_stage3.py =====
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[2]
ok = True

# Credit artifacts
c_models = list((ROOT / "credit_scoring_system" / "models").glob("credit_*"))
if not c_models:
    print("❌ Credit: no model directories found under models/")
    ok = False
# Fraud artifacts
f_models = list((ROOT / "fraud_detection_system" / "models").glob("fraud_*"))
if not f_models:
    print("❌ Fraud: no model directories found under models/")
    ok = False
# Fraud threshold presence
for d in f_models[-1:]:
    thr = d / "threshold.json"
    if not thr.exists():
        print(f"❌ Fraud: threshold.json missing in {d}")
        ok = False
    else:
        t = float(json.loads(thr.read_text()).get("threshold", 0.0))
        if not (0.0 < t < 1.0):
            print(f"❌ Fraud: threshold {t} invalid (expect 0-1).")
            ok = False

if ok:
    print("✅ STAGE 3 HEALTH CHECKS PASSED")
    sys.exit(0)
else:
    sys.exit(1)
# ===== END: health_checks_stage3.py =====