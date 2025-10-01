# ===== BEGIN: run_api.py =====
from pathlib import Path
import sys

# Ensure project root is on sys.path (Windows-safe for import string)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    import uvicorn
    # Use import STRING so --reload works
    uvicorn.run(
        "fraud_detection_system.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(ROOT / "fraud_detection_system" / "api")],
        log_level="info",
    )
# ===== END: run_api.py =====
