# ===== BEGIN: train_credit_models.py (robust split + calibration fallback) =====
import os, json, time, joblib, warnings, re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Iterable, Dict, Any, Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, brier_score_loss, roc_curve
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
import mlflow
from xgboost import XGBClassifier
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]  # repo root
FEAT_PATH = ROOT / "credit_scoring_system" / "data" / "featurestore" / "credit_features.parquet"
RAW_LOANS = ROOT / "credit_scoring_system" / "data" / "raw" / "loans.csv"
MODELS_DIR = ROOT / "credit_scoring_system" / "models"
ARTIF_DIR = MODELS_DIR / "artifacts_credit"
ARTIF_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CARD_DIR = ROOT / "credit_scoring_system" / "docs" / "model_cards"
MODEL_CARD_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR = ROOT / "credit_scoring_system" / "docs" / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = ROOT / "credit_scoring_system" / "config" / "credit_labels_config.json"

# ---------- helpers ----------
def pick_first_col(df: pd.DataFrame, candidates: Iterable[str]) -> str:
    cols_lc = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in cols_lc:
            return cols_lc[cand.lower()]
    raise KeyError(f"None of {list(candidates)} present. Columns: {list(df.columns)[:25]} ...")

def find_col_anycase(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    cols_lc = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lc:
            return cols_lc[cand.lower()]
    return None

def coerce_bool01(s: pd.Series) -> pd.Series:
    s_str = s.astype(str).str.strip().str.lower()
    return s_str.isin(["1","true","yes","y","t"]).astype(int)

def status_to_default_flag(status_series: pd.Series, bad_status_values: Optional[Iterable[str]] = None) -> pd.Series:
    if bad_status_values:
        bad_words = [str(v).strip().lower() for v in bad_status_values]
    else:
        bad_words = ["default","charged off","charge off","write off","written off","bad debt"]
    x = status_series.astype(str).str.strip().str.lower()
    bad = np.zeros(len(x), dtype=bool)
    for w in bad_words:
        bad |= x.str.contains(re.escape(w))
    return pd.Series(bad.astype(int), index=status_series.index)

def load_label_config() -> Dict[str, Any]:
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Env overrides
    col = os.getenv("CREDIT_LABEL_COLUMN")
    kind = os.getenv("CREDIT_LABEL_KIND")  # "binary" or "status"
    bad_vals = os.getenv("CREDIT_BAD_STATUS_VALUES")  # comma-separated
    if col: cfg["label_column"] = col
    if kind: cfg["label_kind"] = kind
    if bad_vals:
        cfg["bad_status_values"] = [v.strip() for v in bad_vals.split(",") if v.strip()]
    return cfg

def preview_loans(loans: pd.DataFrame, borrower_col: str):
    preview = {
        "row_count": int(len(loans)),
        "columns": [{"name": c, "dtype": str(loans[c].dtype)} for c in loans.columns],
        "borrower_col_used": borrower_col,
        "top_values_per_object_col": {}
    }
    for c in loans.columns:
        if loans[c].dtype == "object":
            vc = loans[c].astype(str).str.strip().str.lower().value_counts().head(8)
            preview["top_values_per_object_col"][c] = vc.to_dict()
    (DEBUG_DIR / "loans_columns_preview.json").write_text(json.dumps(preview, indent=2), encoding="utf-8")

def autoscan_status_column(loans: pd.DataFrame) -> Optional[str]:
    hints = ["default","charged off","charge off","write off","written off","bad debt"]
    candidates = []
    for c in loans.columns:
        if loans[c].dtype == "object":
            s = loans[c].astype(str).str.strip().str.lower()
            if any(s.str.contains(re.escape(hint)).any() for hint in hints):
                candidates.append(c)
    name_hints = ["status","state","result","outcome"]
    candidates = sorted(
        set(candidates),
        key=lambda x: (0 if any(h in x.lower() for h in name_hints) else 1, x.lower())
    )
    return candidates[0] if candidates else None

def infer_default_label(loans: pd.DataFrame, borrower_col: str) -> pd.DataFrame:
    cfg = load_label_config()

    # 0) Hard override via config/env
    if "label_column" in cfg and "label_kind" in cfg:
        col = cfg["label_column"]
        kind = cfg["label_kind"].strip().lower()
        if col not in loans.columns:
            col_ci = find_col_anycase(loans, [col])
            if not col_ci:
                raise KeyError(f"Configured label_column '{col}' not found in loans.csv.")
            col = col_ci
        if kind == "binary":
            lbl = loans[[borrower_col, col]].copy().rename(columns={col: "default_flag"})
            if not pd.api.types.is_numeric_dtype(lbl["default_flag"]):
                lbl["default_flag"] = coerce_bool01(lbl["default_flag"])
            else:
                lbl["default_flag"] = (lbl["default_flag"] != 0).astype(int)
            return lbl.groupby(borrower_col, as_index=False)["default_flag"].max()
        elif kind == "status":
            bad_vals = cfg.get("bad_status_values")
            tmp = loans[[borrower_col]].copy()
            tmp["default_flag"] = status_to_default_flag(loans[col], bad_vals)
            return tmp.groupby(borrower_col, as_index=False)["default_flag"].max()
        else:
            raise KeyError("label_kind must be 'binary' or 'status'.")

    # 1) Direct binary columns (aliases)
    binary_aliases = ["default_flag","is_default","defaulted","loan_default","bad_flag","target","y","label","class","Class"]
    col = find_col_anycase(loans, binary_aliases)
    if col is not None:
        lbl = loans[[borrower_col, col]].copy().rename(columns={col: "default_flag"})
        if not pd.api.types.is_numeric_dtype(lbl["default_flag"]):
            lbl["default_flag"] = coerce_bool01(lbl["default_flag"])
        else:
            lbl["default_flag"] = (lbl["default_flag"] != 0).astype(int)
        return lbl.groupby(borrower_col, as_index=False)["default_flag"].max()

    # 2) Status-style columns (aliases)
    status_aliases = ["loan_status","status","loanstatus","current_status","final_status","state","result","outcome"]
    col = find_col_anycase(loans, status_aliases)
    if col is not None:
        tmp = loans[[borrower_col]].copy()
        tmp["default_flag"] = status_to_default_flag(loans[col])
        return tmp.groupby(borrower_col, as_index=False)["default_flag"].max()

    # 3) Autoscan string columns for default/charged off patterns
    col = autoscan_status_column(loans)
    if col is not None:
        tmp = loans[[borrower_col]].copy()
        tmp["default_flag"] = status_to_default_flag(loans[col])
        return tmp.groupby(borrower_col, as_index=False)["default_flag"].max()

    # 4) Nothing found → dump a preview and raise a clear error
    preview_loans(loans, borrower_col)
    raise KeyError(
        "Could not infer a default label. "
        "Options:\n"
        "  A) Create credit_scoring_system/config/credit_labels_config.json like:\n"
        '     {"label_column": "loan_status", "label_kind": "status", "bad_status_values": ["Charged Off","Default"]}\n'
        "  B) Or set env vars CREDIT_LABEL_COLUMN and CREDIT_LABEL_KIND (binary|status), e.g.:\n"
        "     setx CREDIT_LABEL_COLUMN loan_status\n"
        "     setx CREDIT_LABEL_KIND status\n"
        f"  C) Or rename/add a column in loans.csv (e.g., 'default_flag' 0/1).\n"
        f"Debug preview written to: {DEBUG_DIR / 'loans_columns_preview.json'}"
    )

def ks_stat(y_true, y_prob):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    return float(np.max(tpr - fpr))

def gini_from_auc(auc): return 2*auc - 1

def stratified_split_with_min_class(
    X: pd.DataFrame, y: pd.Series, seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Try a few test sizes to keep both classes in train; fallback raises if only one class overall."""
    cls_counts = y.value_counts()
    if cls_counts.nunique() == 1:
        raise ValueError("Only one class present in labels. Need at least one 0 and one 1 to train.")
    for ts in [0.25, 0.2, 0.15, 0.1]:
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=ts, random_state=seed, stratify=y)
        cnt = y_tr.value_counts()
        min_cls = min(cnt.get(0, 0), cnt.get(1, 0))
        if min_cls >= 1:
            return X_tr, X_te, y_tr, y_te
    # last attempt without changing stratify (still stratified), smallest test
    return train_test_split(X, y, test_size=0.1, random_state=seed, stratify=y)

# ---------- main ----------
def main():
    mlflow.set_experiment("credit_stage3_models")
    print(f"Loading features: {FEAT_PATH}")
    feats = pd.read_parquet(FEAT_PATH) if FEAT_PATH.suffix == ".parquet" else pd.read_csv(FEAT_PATH)

    borrower_col = pick_first_col(feats, ["borrower_id", "member_id", "customer_id"])

    loans = pd.read_csv(RAW_LOANS)
    if borrower_col not in loans.columns:
        alias = pick_first_col(loans, ["borrower_id", "member_id", "customer_id"])
        loans = loans.rename(columns={alias: borrower_col})

    labels = infer_default_label(loans, borrower_col)

    print(f"Using loans file: {RAW_LOANS}")
    print("Label column resolved successfully.")

    df = feats.merge(labels, on=borrower_col, how="inner").dropna(subset=["default_flag"])
    y = df["default_flag"].astype(int)
    X = df.drop(columns=["default_flag"])

    num_cols = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    X = X[num_cols].copy()
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X.fillna(X.median(numeric_only=True), inplace=True)

    # Split with safeguards
    X_train, X_test, y_train, y_test = stratified_split_with_min_class(X, y, seed=42)

    # Show class counts
    tr_cnt = y_train.value_counts().to_dict()
    te_cnt = y_test.value_counts().to_dict()
    print(f"Train class counts: {tr_cnt} | Test class counts: {te_cnt}")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_name = f"credit_stage3_{timestamp}"

    with mlflow.start_run(run_name=run_name):
        # Logistic pipeline
        lr_pipe = Pipeline(steps=[
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=200, class_weight="balanced"))
        ])

        # Calibration fallback logic
        min_class_train = min(y_train.value_counts().get(0, 0), y_train.value_counts().get(1, 0))
        if min_class_train >= 3:
            cal_cv = 3
            lr_model = CalibratedClassifierCV(lr_pipe, method="sigmoid", cv=cal_cv)
            lr_model.fit(X_train, y_train)
            lr_prob = lr_model.predict_proba(X_test)[:, 1]
            cal_mode = f"Calibrated (cv={cal_cv})"
        elif min_class_train == 2:
            cal_cv = 2
            lr_model = CalibratedClassifierCV(lr_pipe, method="sigmoid", cv=cal_cv)
            lr_model.fit(X_train, y_train)
            lr_prob = lr_model.predict_proba(X_test)[:, 1]
            cal_mode = f"Calibrated (cv={cal_cv})"
        elif min_class_train == 1:
            # Too few for CV; fit plain LR and use its probabilities (uncalibrated)
            lr_pipe.fit(X_train, y_train)
            lr_prob = lr_pipe.predict_proba(X_test)[:, 1]
            cal_mode = "Uncalibrated (minority count=1)"
        else:
            # Safety: if something odd, fit uncalibrated
            lr_pipe.fit(X_train, y_train)
            lr_prob = lr_pipe.predict_proba(X_test)[:, 1]
            cal_mode = "Uncalibrated (fallback)"

        auc_lr = roc_auc_score(y_test, lr_prob)
        ks_lr = ks_stat(y_test, lr_prob)
        brier_lr = brier_score_loss(y_test, lr_prob)
        gini_lr = gini_from_auc(auc_lr)

        # XGBoost candidate
        cnt = y_train.value_counts()
        scale_pos_weight = float(max(1.0, (cnt.get(0, 1) / cnt.get(1, 1))))
        xgb = XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.08,
            subsample=0.9, colsample_bytree=0.8, reg_lambda=1.0,
            objective="binary:logistic", tree_method="hist",
            random_state=42, scale_pos_weight=scale_pos_weight
        )
        xgb.fit(X_train, y_train)
        xgb_prob = xgb.predict_proba(X_test)[:, 1]

        auc_xgb = roc_auc_score(y_test, xgb_prob)
        ks_xgb = ks_stat(y_test, xgb_prob)
        brier_xgb = brier_score_loss(y_test, xgb_prob)
        gini_xgb = gini_from_auc(auc_xgb)

        # log params/metrics
        mlflow.log_params({
            "features_count": len(num_cols),
            "scale_pos_weight": scale_pos_weight,
            "lr_calibration": cal_mode
        })
        mlflow.log_metrics({
            "auc_lr": auc_lr, "ks_lr": ks_lr, "gini_lr": gini_lr, "brier_lr": brier_lr,
            "auc_xgb": auc_xgb, "ks_xgb": ks_xgb, "gini_xgb": gini_xgb, "brier_xgb": brier_xgb
        })

        # ROC plots
        def plot_roc(y_true, probs, title, out_png):
            fpr, tpr, _ = roc_curve(y_true, probs)
            plt.figure(figsize=(5, 4))
            plt.plot(fpr, tpr, label=f"AUC={roc_auc_score(y_true, probs):.3f}")
            plt.plot([0, 1], [0, 1], '--')
            plt.xlabel("FPR"); plt.ylabel("TPR"); plt.title(title); plt.legend()
            plt.tight_layout(); plt.savefig(out_png); plt.close()

        roc_lr = ARTIF_DIR / f"roc_lr_{timestamp}.png"
        roc_xgb = ARTIF_DIR / f"roc_xgb_{timestamp}.png"
        plot_roc(y_test, lr_prob, "ROC — Logistic (credit)", roc_lr)
        plot_roc(y_test, xgb_prob, "ROC — XGB (credit)", roc_xgb)
        mlflow.log_artifact(str(roc_lr))
        mlflow.log_artifact(str(roc_xgb))

        # persist
        out_dir = MODELS_DIR / f"credit_{timestamp}"
        out_dir.mkdir(parents=True, exist_ok=True)
        # Save the actually used LR model (calibrated or plain)
        try:
            joblib.dump(lr_model, out_dir / "logreg_calibrated_or_plain.joblib")
        except NameError:
            # If we never created lr_model (uncalibrated path), dump lr_pipe instead
            joblib.dump(lr_pipe, out_dir / "logreg_calibrated_or_plain.joblib")
        joblib.dump(xgb,     out_dir / "xgb_model.joblib")
        with open(out_dir / "feature_list.json", "w", encoding="utf-8") as f:
            json.dump({"numeric_features": num_cols}, f, indent=2)

        # model card
        card = {
            "model_family": "credit_pd",
            "timestamp": timestamp,
            "training": {
                "train_class_counts": {int(k): int(v) for k, v in y_train.value_counts().to_dict().items()},
                "test_class_counts": {int(k): int(v) for k, v in y_test.value_counts().to_dict().items()},
                "lr_calibration": cal_mode
            },
            "metrics": {"auc_lr": auc_lr, "ks_lr": ks_lr, "auc_xgb": auc_xgb, "ks_xgb": ks_xgb},
            "notes": "Stage 3 baseline models. Data: borrower-level engineered features; label aggregated from loans."
        }
        with open(MODEL_CARD_DIR / "credit_model.md", "w", encoding="utf-8") as f:
            f.write("# Credit Model Card (Stage 3 Baseline)\n\n")
            f.write(json.dumps(card, indent=2))

        print("✅ Credit Stage 3 training complete.")

if __name__ == "__main__":
    main()
# ===== END: train_credit_models.py =====
