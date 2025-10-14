# ===== BEGIN: app.py (Stage 6 - Shadow Mode) =====
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

# --- Optional SHAP (graceful fallback) ---
try:
    import shap  # type: ignore
    _HAS_SHAP = True
except Exception:
    _HAS_SHAP = False

# --- Paths (repo-root aware) ---
# .../risk_analysis_flagship
ROOT = Path(__file__).resolve().parents[2]
FRAUD_ROOT = ROOT / "fraud_detection_system"
MODELS_DIR = FRAUD_ROOT / "models"
RULES_PATH = FRAUD_ROOT / "rules" / "rules_v1.yml"
LOGS_DIR = FRAUD_ROOT / "api" / "logs"

# ---------- .env support (root .env and/or shared_env/.env) ----------
def _load_dotenv_if_present() -> None:
    """
    Minimal .env loader: reads KEY=VALUE pairs from root .env and shared_env/.env.
    Existing environment variables are not overwritten.
    """
    for env_path in [ROOT / ".env", ROOT / "shared_env" / ".env"]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k and (k not in os.environ):
                    os.environ[k] = v

_load_dotenv_if_present()

# ---------- Utilities ----------
def _latest_model_dir() -> Path:
    """Pick most-recent fraud_* directory under models/ for PRODUCTION."""
    cands = [p for p in MODELS_DIR.glob("fraud_*") if p.is_dir()]
    if not cands:
        raise FileNotFoundError("No fraud_* model directories found under models/.")
    return max(cands, key=lambda p: p.stat().st_mtime)

def _load_rules(path: Path) -> List[Dict[str, Any]]:
    """Load YAML rules list."""
    import yaml  # local import to keep import-time light
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f) or []
    rules: List[Dict[str, Any]] = []
    for r in obj:
        if isinstance(r, dict) and "condition" in r and "name" in r:
            rules.append({"name": str(r["name"]), "condition": str(r["condition"])})
    return rules

def _apply_rules(tx: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[str]:
    """Tiny rules engine, sandboxed eval of boolean expressions on tx dict."""
    hits: List[str] = []
    safe_locals = dict(tx)  # expose fields directly: amount, hour_of_day, etc.
    for rule in rules:
        try:
            cond = rule.get("condition", "")
            if cond and eval(cond, {"__builtins__": {}}, safe_locals):
                hits.append(rule.get("name", "unnamed_rule"))
        except Exception:
            continue
    return hits

# ---------- I/O Schemas ----------
class TransactionIn(BaseModel):
    amount: float = Field(..., ge=0)
    account_age_days: int = Field(..., ge=0)
    country: str = Field("US", min_length=2, max_length=2)
    device_id: str = Field("unknown")
    hour_of_day: int = Field(12, ge=0, le=23)
    # Extend as features grow (keep consistent with training features)

    @validator("country")
    def _upper_iso(cls, v: str) -> str:
        return v.upper()

class ScoreOut(BaseModel):
    decision: str
    proba: float
    rules_hit: List[str]
    top_features: Optional[List[Dict[str, Any]]] = None
    model_timestamp: str
    latency_ms: int

# ---------- App ----------
app = FastAPI(title="Fraud Scoring API", version="1.0")

# Globals (PROD)
_MODEL = None
_THRESHOLD: float = 0.5
_FEATURES: List[str] = []
_RULES: List[Dict[str, Any]] = []
_MODEL_TS = ""

_EXPLAINER = None
_BG = None

# ---------- Candidate globals for SHADOW mode ----------
# Loaded if FRAUD_CANDIDATE_DIR is set; decisions still come from PROD in shadow.
_CAND = None
_CAND_THRESHOLD: float = 0.5
_CAND_FEATURES: List[str] = []
_CAND_TS = ""

# ---------- Traffic toggle ----------
# Step 4 uses only 'shadow' (prod decisions; cand scored + logged).
TRAFFIC_MODE = os.getenv("FRAUD_TRAFFIC_MODE", "prod").lower()  # 'prod' | 'shadow'
CAND_DIR_ENV = os.getenv("FRAUD_CANDIDATE_DIR", "").strip()

# ---------- Model/Explainer loading ----------
def _load_model_bundle() -> None:
    """Load latest PROD model, threshold, features, rules; init SHAP if present."""
    global _MODEL, _THRESHOLD, _FEATURES, _RULES, _MODEL_TS, _EXPLAINER, _BG

    mdir = _latest_model_dir()
    model_path = mdir / "xgb_model.joblib"
    thr_path = mdir / "threshold.json"
    fl_path = mdir / "feature_list.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Missing model file: {model_path}")

    _MODEL = joblib.load(model_path)

    if thr_path.exists():
        try:
            _THRESHOLD = json.loads(thr_path.read_text(encoding="utf-8")).get("threshold", 0.5)
        except Exception:
            _THRESHOLD = 0.5
    else:
        _THRESHOLD = 0.5

    # Features: support list OR {"numeric":[], "categorical":[]}
    if fl_path.exists():
        try:
            fl_obj = json.loads(fl_path.read_text(encoding="utf-8"))
            if isinstance(fl_obj, list):
                _FEATURES = [str(x) for x in fl_obj]
            elif isinstance(fl_obj, dict):
                num = [str(x) for x in (fl_obj.get("numeric") or fl_obj.get("numeric_features") or [])]
                cat = [str(x) for x in (fl_obj.get("categorical") or fl_obj.get("categorical_features") or [])]
                _FEATURES = list(dict.fromkeys([*num, *cat]))
            else:
                _FEATURES = ["amount", "account_age_days", "hour_of_day"]
        except Exception:
            _FEATURES = ["amount", "account_age_days", "hour_of_day"]
    else:
        _FEATURES = ["amount", "account_age_days", "hour_of_day"]

    _RULES = _load_rules(RULES_PATH)
    _MODEL_TS = datetime.fromtimestamp(model_path.stat().st_mtime).isoformat(timespec="seconds")

    # SHAP (optional)
    if _HAS_SHAP:
        try:
            _BG = pd.DataFrame([{f: 0 for f in _FEATURES}])
            _EXPLAINER = shap.TreeExplainer(_MODEL)
        except Exception:
            _EXPLAINER = None

def _load_candidate_bundle(cand_dir: Path) -> None:
    """Load candidate model & metadata for SHADOW scoring (no decisions)."""
    global _CAND, _CAND_THRESHOLD, _CAND_FEATURES, _CAND_TS
    _CAND = None
    _CAND_THRESHOLD = 0.5
    _CAND_FEATURES = []
    _CAND_TS = ""

    if not cand_dir or not cand_dir.exists():
        return

    model_path = cand_dir / "xgb_model.joblib"
    thr_path = cand_dir / "threshold.json"
    fl_path = cand_dir / "feature_list.json"
    if not model_path.exists():
        return

    try:
        _CAND = joblib.load(model_path)
    except Exception:
        _CAND = None
        return

    # threshold
    if thr_path.exists():
        try:
            _CAND_THRESHOLD = json.loads(thr_path.read_text(encoding="utf-8")).get("threshold", 0.5)
        except Exception:
            _CAND_THRESHOLD = 0.5

    # features (union of numeric + categorical)
    if fl_path.exists():
        try:
            fl_obj = json.loads(fl_path.read_text(encoding="utf-8"))
            if isinstance(fl_obj, dict):
                num = [str(x) for x in (fl_obj.get("numeric") or fl_obj.get("numeric_features") or [])]
                cat = [str(x) for x in (fl_obj.get("categorical") or fl_obj.get("categorical_features") or [])]
                _CAND_FEATURES = list(dict.fromkeys([*num, *cat]))
            elif isinstance(fl_obj, list):
                _CAND_FEATURES = [str(x) for x in fl_obj]
        except Exception:
            _CAND_FEATURES = []

    _CAND_TS = datetime.fromtimestamp(model_path.stat().st_mtime).isoformat(timespec="seconds")

def _tx_to_frame(tx: Dict[str, Any], features: List[str]) -> pd.DataFrame:
    row = {f: tx.get(f, 0) for f in features}
    return pd.DataFrame([row], columns=features)

def _predict_proba(model, df: pd.DataFrame) -> float:
    try:
        return float(model.predict_proba(df)[0][1])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

def _top_features(df: pd.DataFrame, k: int = 5) -> Optional[List[Dict[str, Any]]]:
    if _EXPLAINER is None:
        return None
    try:
        vals = _EXPLAINER.shap_values(df)
        row = vals[0] if hasattr(vals, "__len__") else vals
        pairs = list(zip(_FEATURES, row))
        pairs.sort(key=lambda t: abs(float(t[1])), reverse=True)
        return [{"feature": n, "shap_value": float(v)} for n, v in pairs[:k]]
    except Exception:
        return None

# ---------- Daily JSONL logging (LOCAL DATE) ----------
def _write_log(entry: Dict[str, Any]) -> None:
    """
    Append one JSON line to today's file, named with LOCAL date: YYYYMMDD.jsonl.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fname = datetime.now().strftime("%Y%m%d") + ".jsonl"
    with (LOGS_DIR / fname).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def _write_shadow_log(entry: Dict[str, Any]) -> None:
    """
    Append one JSON line to today's SHADOW file: YYYYMMDD_shadow.jsonl
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    fname = datetime.now().strftime("%Y%m%d") + "_shadow.jsonl"
    with (LOGS_DIR / fname).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ---------- FastAPI lifecycle & endpoints ----------
@app.on_event("startup")
def on_startup() -> None:
    _load_model_bundle()
    # Load candidate bundle only if requested (SHADOW)
    if TRAFFIC_MODE == "shadow" and CAND_DIR_ENV:
        cand_path = Path(CAND_DIR_ENV)
        _load_candidate_bundle(cand_path)

@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "traffic_mode": TRAFFIC_MODE,
        "model_timestamp": _MODEL_TS,
        "rules_count": len(_RULES),
        "features_count": len(_FEATURES),
        "features_preview": _FEATURES[:10],
        "candidate_loaded": bool(_CAND),
        "candidate_timestamp": _CAND_TS,
    }

@app.post("/score", response_model=ScoreOut)
def score(payload: TransactionIn) -> ScoreOut:
    t0 = time.perf_counter()

    tx = payload.dict()
    # 1) Rules
    rules_hit = _apply_rules(tx, _RULES) if _RULES else []

    # 2) PROD model (decision path)
    df_prod = _tx_to_frame(tx, _FEATURES)
    proba_prod = _predict_proba(_MODEL, df_prod)
    decision = "flag" if (proba_prod >= _THRESHOLD or len(rules_hit) > 0) else "allow"
    tops = _top_features(df_prod)

    latency_prod_ms = int((time.perf_counter() - t0) * 1000)

    # 3) Log regular prod record (LOCAL date filename; local timestamp)
    _write_log({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "tx": tx,
        "proba": proba_prod,
        "decision": decision,
        "rules_hit": rules_hit,
        "latency_ms": latency_prod_ms,
        "model_ts": _MODEL_TS,
    })

    # 4) SHADOW scoring (no decision impact)
    if TRAFFIC_MODE == "shadow" and _CAND is not None:
        t1 = time.perf_counter()
        # build df using candidate's own feature list (may include country/device_id)
        cand_features = _CAND_FEATURES if _CAND_FEATURES else _FEATURES
        df_cand = _tx_to_frame(tx, cand_features)
        proba_cand = _predict_proba(_CAND, df_cand)
        latency_cand_ms = int((time.perf_counter() - t1) * 1000)
        decision_cand = "flag" if proba_cand >= _CAND_THRESHOLD else "allow"

        _write_shadow_log({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "payload": tx,
            "prod": {
                "proba": proba_prod,
                "decision": decision,
                "rules_hit": rules_hit,
            },
            "cand": {
                "proba": proba_cand,
                "decision": decision_cand,
            },
            "latency_ms": {"prod": latency_prod_ms, "cand": latency_cand_ms},
            "model_ts": {"prod": _MODEL_TS, "cand": _CAND_TS},
        })

    return ScoreOut(
        decision=decision,
        proba=proba_prod,
        rules_hit=rules_hit,
        top_features=tops,
        model_timestamp=_MODEL_TS,
        latency_ms=latency_prod_ms,
    )
# ===== END: app.py (Stage 6 - Shadow Mode) =====
