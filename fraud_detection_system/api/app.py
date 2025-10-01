# ===== BEGIN: app.py =====
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

# Optional SHAP (graceful fallback)
try:
    import shap  # type: ignore
    _HAS_SHAP = True
except Exception:
    _HAS_SHAP = False

# Paths
ROOT = Path(__file__).resolve().parents[2]  # ...\risk_analysis_flagship
FRAUD_ROOT = ROOT / "fraud_detection_system"
MODELS_DIR = FRAUD_ROOT / "models"
RULES_PATH = FRAUD_ROOT / "rules" / "rules_v1.yml"
LOGS_DIR = FRAUD_ROOT / "api" / "logs"

# Discover latest model folder
def _latest_model_dir() -> Path:
    cands = [p for p in MODELS_DIR.glob("fraud_*") if p.is_dir()]
    if not cands:
        raise FileNotFoundError("No fraud_* model directories found.")
    return max(cands, key=lambda p: p.stat().st_mtime)

# Minimal rules engine (YAML)
def _load_rules(path: Path) -> List[Dict[str, Any]]:
    import yaml  # local import to keep app import light
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []

def _apply_rules(tx: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[str]:
    # NOTE: Simple eval with safe locals; production would use a parser.
    hits = []
    safe = dict(tx)
    for rule in rules:
        try:
            if eval(rule["condition"], {"__builtins__": {}}, safe):
                hits.append(rule["name"])
        except Exception:
            # skip invalid rule gracefully
            continue
    return hits

# Pydantic input schema (keep aligned with features)
class TransactionIn(BaseModel):
    amount: float = Field(..., ge=0)
    account_age_days: int = Field(..., ge=0)
    country: str = Field("US", min_length=2, max_length=2)
    device_id: str = Field("unknown")
    hour_of_day: int = Field(12, ge=0, le=23)
    # Extend freely as your features grow

    @validator("country")
    def _upper_iso(cls, v: str) -> str:
        return v.upper()

# Response model
class ScoreOut(BaseModel):
    decision: str
    proba: float
    rules_hit: List[str]
    top_features: Optional[List[Dict[str, Any]]] = None
    model_timestamp: str
    latency_ms: int

app = FastAPI(title="Fraud Scoring API", version="1.0")

# Globals loaded at startup
_MODEL = None
_THRESHOLD = 0.5
_FEATURES: List[str] = []
_RULES: List[Dict[str, Any]] = []
_MODEL_TS = ""

_EXPLAINER = None
_BG = None

def _load_model_bundle():
    global _MODEL, _THRESHOLD, _FEATURES, _RULES, _MODEL_TS, _EXPLAINER, _BG
    mdir = _latest_model_dir()
    model_path = mdir / "xgb_model.joblib"
    thr_path = mdir / "threshold.json"
    fl_path = mdir / "feature_list.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Missing model file: {model_path}")
    _MODEL = joblib.load(model_path)

    if thr_path.exists():
        _THRESHOLD = json.loads(thr_path.read_text(encoding="utf-8")).get("threshold", 0.5)
    else:
        _THRESHOLD = 0.5

    if fl_path.exists():
        fl_obj = json.loads(fl_path.read_text(encoding="utf-8"))
        if isinstance(fl_obj, list):
            _FEATURES = fl_obj
        elif isinstance(fl_obj, dict):
            num = fl_obj.get("numeric_features", []) or []
            cat = fl_obj.get("categorical_features", []) or []
            # dedupe, preserve order
            _FEATURES = list(dict.fromkeys([*num, *cat]))
        else:
            _FEATURES = ["amount", "account_age_days", "hour_of_day"]  # safe fallback
    else:
        _FEATURES = ["amount", "account_age_days", "hour_of_day"]

    _RULES = _load_rules(RULES_PATH) if RULES_PATH.exists() else []
    _MODEL_TS = datetime.fromtimestamp(model_path.stat().st_mtime).isoformat(timespec="seconds")

    # SHAP init (optional)
    if _HAS_SHAP:
        try:
            _BG = pd.DataFrame([{f: 0 for f in _FEATURES}])
            _EXPLAINER = shap.TreeExplainer(_MODEL)
        except Exception:
            _EXPLAINER = None

def _tx_to_frame(tx: Dict[str, Any]) -> pd.DataFrame:
    # Build a single-row DataFrame aligned to training features.
    row = {f: tx.get(f, 0) for f in _FEATURES}
    return pd.DataFrame([row], columns=_FEATURES)

def _predict_proba(df: pd.DataFrame) -> float:
    # XGB returns [ [p0, p1] ]
    proba = float(_MODEL.predict_proba(df)[0][1])
    return proba

def _top_features(df: pd.DataFrame, k: int = 5) -> Optional[List[Dict[str, Any]]]:
    if _EXPLAINER is None:
        return None
    try:
        vals = _EXPLAINER.shap_values(df)
        # shap_values may be array-like; take first row
        row = vals[0] if hasattr(vals, "__len__") else vals
        pairs = list(zip(_FEATURES, row))
        pairs.sort(key=lambda t: abs(float(t[1])), reverse=True)
        return [{"feature": n, "shap_value": float(v)} for n, v in pairs[:k]]
    except Exception:
        return None

def _write_log(entry: Dict[str, Any]) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fname = datetime.utcnow().strftime("%Y%m%d") + ".jsonl"
    with (LOGS_DIR / fname).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

@app.on_event("startup")
def on_startup():
    _load_model_bundle()

@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "model_timestamp": _MODEL_TS,
        "rules_count": len(_RULES),
        "features_count": len(_FEATURES),
        "features_preview": _FEATURES[:10],
    }

@app.post("/score", response_model=ScoreOut)
def score(payload: TransactionIn) -> ScoreOut:
    t0 = time.perf_counter()

    tx = payload.dict()
    # 1) Rules
    rules_hit = _apply_rules(tx, _RULES) if _RULES else []

    # 2) Model
    df = _tx_to_frame(tx)
    proba = _predict_proba(df)
    decision = "flag" if (proba >= _THRESHOLD or len(rules_hit) > 0) else "allow"
    tops = _top_features(df)

    # 3) Log
    latency_ms = int((time.perf_counter() - t0) * 1000)
    _write_log({
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        "tx": tx,
        "proba": proba,
        "decision": decision,
        "rules_hit": rules_hit,
        "latency_ms": latency_ms,
        "model_ts": _MODEL_TS,
    })

    return ScoreOut(
        decision=decision,
        proba=proba,
        rules_hit=rules_hit,
        top_features=tops,
        model_timestamp=_MODEL_TS,
        latency_ms=latency_ms,
    )
# ===== END: app.py =====