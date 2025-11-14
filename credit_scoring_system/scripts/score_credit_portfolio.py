# ===== BEGIN: score_credit_portfolio.py =====
from __future__ import annotations
import os, sys, json, glob, math, warnings, mlflow
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
import joblib

PROJECT_ROOT = Path(r"C:\DevProjects\risk_analysis_flagship")
mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", f"file:///{(PROJECT_ROOT / 'mlruns').as_posix()}"))
mlflow.set_experiment("credit_stage4_scoring")

# Optional deps
try:
    import mlflow
except Exception:
    mlflow = None

# SHAP is optional, enabled only via env var
_ENABLE_SHAP = os.getenv("ENABLE_SHAP", "0") == "1"
if _ENABLE_SHAP:
    try:
        import shap
        _HAS_SHAP = True
    except Exception:
        _HAS_SHAP = False
        shap = None
else:
    _HAS_SHAP = False
    shap = None


ROOT = Path(__file__).resolve().parents[2]  # .../risk_analysis_flagship
CONFIG_PATH = ROOT / "credit_scoring_system" / "config" / "credit_scoring_config.json"

def _read_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Allow LGD override via env
    env_lgd = os.getenv("LGD_DEFAULT")
    if env_lgd is not None:
        try:
            cfg["lgd_default"] = float(env_lgd)
        except ValueError:
            print(f"[WARN] LGD_DEFAULT env '{env_lgd}' invalid; using config value {cfg.get('lgd_default')}")
    return cfg

def _latest_model_dir(pattern: str) -> Optional[Path]:
    dirs = [Path(p) for p in glob.glob(str(ROOT / pattern)) if Path(p).is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)

def _pick_model_file(model_dir: Path, preference: List[str]) -> Optional[Path]:
    for name in preference:
        cand = model_dir / name
        if cand.exists():
            return cand
    # fallback: any .joblib in the dir
    any_jobs = list(model_dir.glob("*.joblib"))
    return any_jobs[0] if any_jobs else None

def _read_features(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except Exception:
        # Parquet engine missing? Fall back to CSV with same path stem
        csv_path = path.with_suffix(".csv")
        if csv_path.exists():
            return pd.read_csv(csv_path)
        raise

def _timestamp_guard(raw_path: Path, features_path: Path):
    raw_m = raw_path.stat().st_mtime
    feat_m = features_path.stat().st_mtime
    if raw_m > feat_m:
        raw_dt = datetime.fromtimestamp(raw_m)
        feat_dt = datetime.fromtimestamp(feat_m)
        msg = (
            f"[ERROR] Timestamp guard triggered: raw loans ({raw_dt}) is newer than features ({feat_dt}).\n"
            f"Rebuild features BEFORE scoring to avoid stale joins.\n"
            f"Hint: Right-click build_features_credit.py → Run Python File in Terminal."
        )
        print(msg)
        sys.exit(2)

def _load_feature_list(model_dir: Path) -> Optional[List[str]]:
    fl = model_dir / "feature_list.json"
    if fl.exists():
        try:
            with open(fl, "r", encoding="utf-8") as f:
                obj = json.load(f)
                if isinstance(obj, dict) and "features" in obj:
                    return obj["features"]
                if isinstance(obj, list):
                    return obj
        except Exception:
            pass
    return None

def _prepare_X(df_feat: pd.DataFrame, id_col: str, allowed: Optional[List[str]]) -> pd.DataFrame:
    # Keep only numeric columns; drop identifiers and obviously non-features
    drop_cols = {id_col}
    candidates = df_feat.select_dtypes(include=[np.number]).columns.tolist()
    keep = [c for c in candidates if c not in drop_cols]
    if allowed:
        # Intersect with allowed list
        keep = [c for c in keep if c in set(allowed)]
    X = df_feat[keep].copy()
    # Replace inf/-inf with nan, then fill with 0
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0.0)
    return X

def _predict_pd(model, X):
    """
    Predict PD with feature-alignment and a shape-mismatch fallback.

    - First, try to align by feature names if the model exposes them.
    - If XGBoost raises "Feature shape mismatch, expected: N, got M",
      drop extra columns to match N and retry once.
    """

    def _align_by_feature_names(model, data):
        """Best-effort alignment using model feature metadata (if available)."""
        if not hasattr(data, "columns"):
            return data  # not a DataFrame, nothing to align

        feature_names = None

        # 1) sklearn-style feature_names_in_
        feature_names_in = getattr(model, "feature_names_in_", None)
        if feature_names_in is not None:
            feature_names = list(feature_names_in)

        # 2) Raw XGBoost booster feature names
        if feature_names is None and hasattr(model, "get_booster"):
            try:
                booster = model.get_booster()
            except Exception:
                booster = None
            if booster is not None and getattr(booster, "feature_names", None):
                # Only trust these if they actually exist in the DataFrame
                booster_names = list(booster.feature_names)
                if all(name in data.columns for name in booster_names):
                    feature_names = booster_names

        # 3) If we discovered compatible feature names, subset + order
        if feature_names is not None:
            missing = [f for f in feature_names if f not in data.columns]
            if missing:
                # If names clearly don't match, don't try to force it here.
                # We'll rely on the shape-based fallback instead.
                return data
            data = data[feature_names]

        return data

    def _call_with_shape_fallback(predict_fn, data):
        """
        Call predict_fn(data). If XGBoost complains about feature shape mismatch,
        parse "expected: N, got M" from the message and retry with N columns.
        """
        # First, try to align by feature names (if possible)
        data = _align_by_feature_names(model, data)

        # Ensure numeric if it's a DataFrame
        if hasattr(data, "astype"):
            data = data.astype(float)

        try:
            return predict_fn(data)
        except ValueError as e:
            msg = str(e)
            if "Feature shape mismatch" not in msg or "expected:" not in msg or "got" not in msg:
                # Different error → bubble up
                raise

            # Try to parse "expected: 4, got 6"
            try:
                after_expected = msg.split("expected:", 1)[1]
                first_part, rest = after_expected.split(",", 1)
                expected = int(first_part.strip())
                after_got = rest.split("got", 1)[1]
                got_str = after_got.strip().split()[0]
                got = int(got_str)
            except Exception:
                # Parsing failed → re-raise original
                raise

            # Only attempt a fix if we truly have *more* features than expected
            if got <= expected:
                raise

            # Drop extra columns/features to match "expected"
            if hasattr(data, "iloc"):  # pandas DataFrame
                data_fixed = data.iloc[:, :expected]
            else:
                arr = np.asarray(data, dtype=float)
                if arr.ndim != 2 or arr.shape[1] < expected:
                    raise
                data_fixed = arr[:, :expected]

            # Second (and last) attempt
            return predict_fn(data_fixed)

    # 1) Prefer predict_proba
    if hasattr(model, "predict_proba"):
        try:
            proba = _call_with_shape_fallback(model.predict_proba, X)
            proba = np.asarray(proba, dtype=float)
            # Handle both (n_samples,) and (n_samples, 2) shapes
            if proba.ndim == 2 and proba.shape[1] > 1:
                proba = proba[:, 1]
            return proba.reshape(-1)
        except Exception:
            pass

    # 2) Fallback: decision_function → logistic transform
    if hasattr(model, "decision_function"):
        try:
            d = _call_with_shape_fallback(model.decision_function, X)
            d = np.asarray(d, dtype=float).reshape(-1)
            return 1.0 / (1.0 + np.exp(-d))
        except Exception:
            pass

    # 3) Last resort: predict → cast to float, clipped to [0, 1]
    pred = _call_with_shape_fallback(model.predict, X)
    return np.clip(np.asarray(pred, dtype=float).reshape(-1), 0.0, 1.0)



def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def _safe_to_parquet(df: pd.DataFrame, path: Path):
    try:
        df.to_parquet(path, index=False)
    except Exception:
        # fallback to CSV
        df.to_csv(path.with_suffix(".csv"), index=False)

def _make_rollups(df_scores: pd.DataFrame, seg_keys: List[str], id_col: str) -> pd.DataFrame:
    g = df_scores.groupby(seg_keys, dropna=False)
    out = g.agg(
        borrowers=(id_col, "nunique"),
        total_EAD=("EAD", "sum"),
        avg_PD=("PD", "mean"),
        total_EL=("EL", "sum"),
    ).reset_index()
    return out

def _maybe_log_mlflow(summary: dict, artifacts_dir: Path):
    if mlflow is None:
        print("[INFO] MLflow not available; skipping tracking")
        return
    try:
        mlflow.set_tag("stage4_credit_batch_scoring", "true")
        for k, v in summary.items():
            if isinstance(v, (int, float)) and not math.isnan(v):
                mlflow.log_metric(k, float(v))
        # Log artifacts folder if small; else just key files
        if artifacts_dir.exists():
            for p in artifacts_dir.glob("*"):
                try:
                    mlflow.log_artifact(str(p))
                except Exception:
                    pass
    except Exception as e:
        print(f"[WARN] MLflow logging skipped: {e}")

def _maybe_shap(model, X_sample: pd.DataFrame, out_png: Path):
    if not _HAS_SHAP:
        return
    try:
        explainer = shap.Explainer(model, X_sample)
        vals = explainer(X_sample)
        import matplotlib.pyplot as plt
        shap.summary_plot(vals, X_sample, show=False, max_display=20)
        plt.tight_layout()
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png, dpi=150)
        plt.close()
    except Exception as e:
        print(f"[WARN] SHAP skipped: {e}")

def main():
    cfg = _read_config(CONFIG_PATH)
    id_col = cfg["id_column"]
    ead_col = cfg["ead_column"]
    seg_keys = cfg["segment_keys"]
    lgd_default = float(cfg["lgd_default"])
    features_path = ROOT / cfg["features_path"]
    loans_path = ROOT / cfg["raw_loans_path"]

    # Timestamp guard (optional via config)
    if cfg.get("timestamp_guard", True):
        _timestamp_guard(loans_path, features_path)

    # Load data
    feat = _read_features(features_path)
    loans = pd.read_csv(loans_path)

    # Sanity columns
    for c in [id_col, ead_col, *seg_keys]:
        if c not in loans.columns:
            raise AssertionError(f"Missing required column in raw loans: '{c}'")

    # Combine to get EAD + segments on the feature rows
    base = feat.merge(
        loans[[id_col, ead_col, *seg_keys]].drop_duplicates(id_col),
        on=id_col,
        how="left",
        validate="m:1",
    )

    # Locate model
    model_dir = _latest_model_dir(cfg["model_dir_glob"])
    if model_dir is None:
        raise FileNotFoundError("No credit_* model directories found. Train Stage 3 models first.")
    model_file = _pick_model_file(model_dir, cfg["pd_model_preference"])
    if model_file is None:
        raise FileNotFoundError(f"No model file found in {model_dir}. Expected one of {cfg['pd_model_preference']}.")
    model = joblib.load(model_file)

    # Feature list awareness (prefer what the model says it saw at fit)
    allowed_from_file = _load_feature_list(model_dir)  # may be None or []
    # Build numeric matrix first (all numeric, minus ID)
    X_all = _prepare_X(base, id_col=id_col, allowed=None)

    expected: Optional[List[str]] = None

    # 1) scikit-learn-style feature_names_in_
    feature_names_in = getattr(model, "feature_names_in_", None)
    if feature_names_in is not None and len(feature_names_in) > 0:
        expected = list(feature_names_in)

    # 2) Raw XGBoost booster feature names (only if they fit the DataFrame)
    if expected is None and hasattr(model, "get_booster"):
        try:
            booster = model.get_booster()
            booster_names = getattr(booster, "feature_names", None)
            if booster_names and all(name in X_all.columns for name in booster_names):
                expected = list(booster_names)
        except Exception:
            pass

    # 3) Fall back to feature_list.json, filtered to existing columns
    if expected is None and allowed_from_file:
        expected = [c for c in allowed_from_file if c in X_all.columns]

    # 4) Final alignment or fallback
    if expected:
        missing_for_model = [c for c in expected if c not in X_all.columns]
        if missing_for_model:
            raise AssertionError(
                "Your features parquet is missing columns required by the model: "
                + ", ".join(missing_for_model)
            )
        X = X_all.reindex(columns=expected, fill_value=0.0)
    else:
        # No explicit list; proceed with all numeric (original behavior)
        X = X_all



    # Predict PD
    pd_hat = _predict_pd(model, X)

    # LGD: use column if present; else default
    lgd_vec = base["LGD"].astype(float).values if "LGD" in base.columns else np.full(len(base), lgd_default, dtype=float)
    ead_vec = base[ead_col].astype(float).fillna(0.0).values

    # Expected Loss
    el_vec = pd_hat * lgd_vec * ead_vec

    # Assemble scores dataframe
    scores = pd.DataFrame({
        id_col: base[id_col].values,
        "PD": pd_hat,
        "EAD": ead_vec,
        "LGD": lgd_vec,
        "EL": el_vec
    })
    # Preserve segment keys for rollups
    for k in seg_keys:
        scores[k] = base[k].values

    # Outputs (dated)
    out_dir = ROOT / "credit_scoring_system" / "outputs" / "scoring"
    _ensure_dir(out_dir)
    datestr = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d")
    pd_path = out_dir / f"pd_scores_{datestr}.parquet"
    seg_path = out_dir / f"segment_rollups_{datestr}.parquet"

    _safe_to_parquet(scores[[id_col, "PD", "EAD", "LGD", "EL"] + seg_keys], pd_path)

    # Rollups
    rollups = _make_rollups(scores, seg_keys=seg_keys, id_col=id_col)
    _safe_to_parquet(rollups, seg_path)

    # Summary
    n = len(scores)
    avg_pd = float(np.mean(pd_hat)) if n else float("nan")
    total_el = float(np.sum(el_vec)) if n else 0.0
    print(f"✅ Credit Stage 4 scoring complete | N={n} | avg_PD={avg_pd:.6f} | total_EL={total_el:,.2f}")
    print(f"→ Scores:   {pd_path}")
    print(f"→ Rollups:  {seg_path}")
    print(f"→ Model:    {model_file}")

    # MLflow tracking (optional)
    summary = {"avg_PD": avg_pd, "total_EL": total_el}
    artifacts_dir = out_dir
    _maybe_log_mlflow(summary, artifacts_dir)

    # Optional SHAP preview for top borrowers by PD (only if enabled via env var)
    if _ENABLE_SHAP and _HAS_SHAP:
        try:
            top_idx = np.argsort(pd_hat)[-200:] if n > 200 else np.arange(n)
            X_sample = X.iloc[top_idx].copy()
            shap_png = ROOT / "credit_scoring_system" / "models" / "artifacts_credit" / f"shap_summary_{datestr}.png"
            _maybe_shap(model, X_sample, shap_png)
        except Exception as e:
            print(f"[WARN] SHAP skipped due to error: {e}")


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()
# ===== END: score_credit_portfolio.py =====
