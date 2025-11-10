# credit_scoring_system/api/app.py
# Clean FastAPI app for Credit Scoring (Pydantic v2 safe, no custom models)

from __future__ import annotations

import os
import json
from typing import Any, Dict, List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse

APP_TITLE = "Credit Scoring API"
APP_VERSION = "1.2.0"
DEFAULT_THRESHOLD = 0.20

# Resolve repo root from this file location (robust even if CWD differs)
HERE = os.path.abspath(os.path.dirname(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODELS_ROOT = os.path.join(REPO_ROOT, "credit_scoring_system", "models")

JSON_POINTER = os.path.join(MODELS_ROOT, "PROD_POINTER.json")
TXT_POINTER = os.path.join(MODELS_ROOT, "PROD_POINTER.txt")
CONVENTIONAL_PROD = os.path.join(MODELS_ROOT, "PROD")

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# -----------------------------
# helpers
# -----------------------------
def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

def _parse_feature_list(raw: Any) -> List[str]:
    """
    Accept one of:
      - list: ["f1", "f2", ...]
      - dict of lists: {"features":[...]} or {"numeric_features":[...], "categorical_features":[...], "binary_features":[...]}
    Return flat, de-duplicated list.
    """
    if isinstance(raw, list):
        return _dedupe_preserve_order([str(x) for x in raw])

    if isinstance(raw, dict):
        merged: List[str] = []
        if isinstance(raw.get("features"), list):
            merged.extend([str(x) for x in raw["features"]])
        for bucket in ("numeric_features", "categorical_features", "binary_features"):
            v = raw.get(bucket)
            if isinstance(v, list):
                merged.extend([str(x) for x in v])
        return _dedupe_preserve_order(merged)

    raise RuntimeError("feature_list.json not understood (expected list or dict of lists).")

def _resolve_prod_dir() -> str:
    # 1) env var
    env_dir = os.getenv("CREDIT_PROD_DIR")
    if env_dir and os.path.isdir(env_dir):
        return os.path.abspath(env_dir)

    # 2) JSON pointer
    if os.path.isfile(JSON_POINTER):
        try:
            with open(JSON_POINTER, "r", encoding="utf-8") as f:
                p = json.load(f)
            if isinstance(p, dict) and "prod_dir" in p:
                candidate = p["prod_dir"]
                if not os.path.isabs(candidate):
                    candidate = os.path.join(MODELS_ROOT, candidate)
                if os.path.isdir(candidate):
                    return os.path.abspath(candidate)
        except Exception:
            pass

    # 3) TXT pointer
    if os.path.isfile(TXT_POINTER):
        try:
            with open(TXT_POINTER, "r", encoding="utf-8") as f:
                line = f.read().strip()
            candidate = line
            if candidate and not os.path.isabs(candidate):
                candidate = os.path.join(MODELS_ROOT, candidate)
            if candidate and os.path.isdir(candidate):
                return os.path.abspath(candidate)
        except Exception:
            pass

    # 4) conventional PROD
    if os.path.isdir(CONVENTIONAL_PROD):
        return os.path.abspath(CONVENTIONAL_PROD)

    raise RuntimeError(
        "Could not resolve CREDIT PROD model directory. "
        "Set CREDIT_PROD_DIR, or add PROD_POINTER.json/.txt, or create models/PROD."
    )

def _load_threshold(thr_path: str) -> float:
    if not os.path.isfile(thr_path):
        return DEFAULT_THRESHOLD
    try:
        with open(thr_path, "r", encoding="utf-8") as f:
            t = json.load(f)
        val = t.get("pd_threshold", t.get("threshold", DEFAULT_THRESHOLD))
        return float(val)
    except Exception:
        return DEFAULT_THRESHOLD

def _get_proba(model, X: pd.DataFrame) -> List[float]:
    # Prefer predict_proba -> [p1], else decision_function/predict
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        try:
            return [float(p) for p in proba[:, 1]]
        except Exception:
            return [float(p) for p in proba]
    if hasattr(model, "decision_function"):
        df = model.decision_function(X)
        return [float(p) for p in df]
    pred = model.predict(X)
    return [float(p) for p in pred]

# -----------------------------
# Model bundle
# -----------------------------
class ModelBundle:
    model = None
    feature_list: List[str] = []
    threshold: float = DEFAULT_THRESHOLD
    prod_dir: str | None = None
    load_error: Exception | None = None

    @classmethod
    def load(cls) -> None:
        try:
            prod = _resolve_prod_dir()
            cls.prod_dir = prod

            model_path = os.path.join(prod, "xgb_model.joblib")  # adjust if needed
            feats_path = os.path.join(prod, "feature_list.json")
            thr_path = os.path.join(prod, "threshold.json")

            if not os.path.isfile(model_path):
                raise RuntimeError(f"Missing model file: {model_path}")
            if not os.path.isfile(feats_path):
                raise RuntimeError(f"Missing feature_list.json: {feats_path}")

            cls.model = joblib.load(model_path)

            with open(feats_path, "r", encoding="utf-8") as f:
                raw_feats = json.load(f)
            cls.feature_list = _parse_feature_list(raw_feats)
            if not cls.feature_list:
                raise RuntimeError("Resolved feature_list is empty after parsing feature_list.json")

            cls.threshold = _load_threshold(thr_path)
            cls.load_error = None
        except Exception as e:
            cls.model = None
            cls.feature_list = []
            cls.threshold = DEFAULT_THRESHOLD
            cls.prod_dir = None
            cls.load_error = e

# Load at startup (non-fatal; report via /health)
ModelBundle.load()

# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
def health():
    if ModelBundle.load_error:
        return JSONResponse(status_code=503, content={"ok": False, "error": str(ModelBundle.load_error)})
    return {
        "ok": True,
        "features": len(ModelBundle.feature_list),
        "threshold": ModelBundle.threshold,
        "model_dir": ModelBundle.prod_dir,
        "model_class": type(ModelBundle.model).__name__ if ModelBundle.model is not None else None,
        "version": APP_VERSION,
    }

@app.get("/features")
def features():
    if ModelBundle.load_error:
        raise HTTPException(status_code=503, detail=str(ModelBundle.load_error))
    return {"features": ModelBundle.feature_list}

@app.post("/reload")
def reload_model():
    ModelBundle.load()
    if ModelBundle.load_error:
        return JSONResponse(status_code=503, content={"ok": False, "error": str(ModelBundle.load_error)})
    return {"ok": True, "model_dir": ModelBundle.prod_dir, "features": len(ModelBundle.feature_list)}

@app.post("/score")
def score_one(record: Dict[str, Any] = Body(...)):
    if ModelBundle.load_error:
        raise HTTPException(status_code=503, detail=str(ModelBundle.load_error))

    X = pd.DataFrame([record]).reindex(columns=ModelBundle.feature_list, fill_value=0)
    try:
        p = float(_get_proba(ModelBundle.model, X)[0])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scoring error: {e}")

    return {"pd": p, "threshold": ModelBundle.threshold, "decision": int(p >= ModelBundle.threshold)}

@app.post("/score_batch")
def score_batch(payload: Dict[str, Any] = Body(...)):
    """
    Expect: {"records": [ {...}, {...} ]}
    """
    if ModelBundle.load_error:
        raise HTTPException(status_code=503, detail=str(ModelBundle.load_error))

    recs = payload.get("records")
    if not isinstance(recs, list):
        raise HTTPException(status_code=422, detail='Body must be {"records": [ {...}, {...} ]}')

    rows: List[Dict[str, Any]] = []
    for r in recs:
        if isinstance(r, dict):
            rows.append(r)
        else:
            try:
                rows.append(dict(r))
            except Exception:
                raise HTTPException(status_code=422, detail="Each record must be a JSON object (dict).")

    if not rows:
        return {"count": 0, "results": []}

    X = pd.DataFrame(rows).reindex(columns=ModelBundle.feature_list, fill_value=0)
    try:
        proba = _get_proba(ModelBundle.model, X)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scoring error: {e}")

    results = [
        {"pd": float(p), "threshold": ModelBundle.threshold, "decision": int(float(p) >= ModelBundle.threshold)}
        for p in proba
    ]

    # Optional debug echo
    debug = None
    if os.getenv("CREDIT_API_DEBUG") == "1":
        debug = {
            "features_used": ModelBundle.feature_list,
            "X_head": X.head(5).to_dict(orient="records"),
            "rows": len(X),
            "model_dir": ModelBundle.prod_dir,
        }

    return {"count": len(results), "results": results, "debug": debug}
