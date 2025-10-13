from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier


# ---------- Paths ----------
ROOT = Path(__file__).resolve().parents[2]  # .../risk_analysis_flagship
FRAUD = ROOT / "fraud_detection_system"

CFG = FRAUD / "config" / "fraud_labels_config.json"
TRAIN_LABELED = FRAUD / "data" / "training" / "transactions_labeled.csv"
RAW_NO_LABEL = FRAUD / "data" / "raw" / "transactions.csv"
LABELS_DIR = FRAUD / "data" / "labels"  # contains transactions_labels_*.csv for optional join

MODELS = FRAUD / "models"
RUN_TS = datetime.now().strftime("%Y%m%d")
CAND_DIR = MODELS / f"CAND_{RUN_TS}"
CAND_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Feature schema (will auto-subset to columns that exist) ----------
NUMERIC_DEFAULT = ["amount", "account_age_days", "hour_of_day"]
CATEG_DEFAULT = ["country", "device_id"]


def _read_label_from_cfg() -> str | None:
    if CFG.exists():
        try:
            val = json.load(open(CFG, "r", encoding="utf-8")).get("label_column")
            return val if isinstance(val, str) and val.strip() else None
        except Exception:
            return None
    return None


def _load_dataframe(label_col: str | None) -> tuple[pd.DataFrame, str, str]:
    """
    Returns: (df, label_col_used, data_source)
    Priority:
      1) training/transactions_labeled.csv (must contain label_col)
      2) raw/transactions.csv + LABELS_DIR auto-join by txn_id
    """
    # 1) Labeled training file
    if TRAIN_LABELED.exists():
        df = pd.read_csv(TRAIN_LABELED)
        # If config label not found, try to infer from common names
        if label_col is None:
            for c in ["is_fraud", "is_chargeback", "label", "fraud_flag", "chargeback"]:
                if c in df.columns:
                    label_col = c
                    break
        if label_col and label_col in df.columns:
            return df, label_col, "training_labeled"

    # 2) Raw + labels auto-join by txn_id
    if RAW_NO_LABEL.exists():
        base = pd.read_csv(RAW_NO_LABEL)
        # Need txn_id to join; otherwise we cannot enrich
        if "txn_id" not in base.columns:
            raise SystemExit(
                f"Raw file found at {RAW_NO_LABEL} but it has no 'txn_id' to join labels. "
                f"Either: (a) add training file {TRAIN_LABELED} that already includes labels, "
                f"or (b) add txn_id to both raw and labels CSVs."
            )
        lbl = None
        if LABELS_DIR.exists():
            lbl_files = sorted(LABELS_DIR.glob("transactions_labels_*.csv"))
            if lbl_files:
                lbl = pd.read_csv(lbl_files[-1])  # newest
        if lbl is None or "txn_id" not in lbl.columns:
            raise SystemExit(
                f"No usable labels in {LABELS_DIR}. Add a file like "
                f"'transactions_labels_YYYY-MM.csv' with columns: txn_id,{label_col or 'is_fraud'} "
                f"or point to a labeled training file {TRAIN_LABELED}."
            )
        df = base.merge(lbl, on="txn_id", how="inner")
        # If config label not found in merged, infer
        if label_col is None or label_col not in df.columns:
            for c in ["is_fraud", "is_chargeback", "label", "fraud_flag", "chargeback"]:
                if c in df.columns:
                    label_col = c
                    break
        if label_col and label_col in df.columns:
            return df, label_col, "raw_plus_labels_join"

    # If we reached here, we couldn't find any labels
    raise SystemExit(
        "Could not find a dataset with labels.\n"
        f"- Checked: {TRAIN_LABELED} (should already include a label column), and\n"
        f"- Attempted: {RAW_NO_LABEL} + newest labels in {LABELS_DIR} joined by txn_id.\n"
        "Fix one of the two sources, or update fraud_labels_config.json with the correct 'label_column'."
    )


def _onehot_encoder():
    # Use sparse=False for broad compatibility with sklearn versions
    return OneHotEncoder(handle_unknown="ignore", sparse=False)


def main():
    label_from_cfg = _read_label_from_cfg()

    # Load df with labels (from training file or raw+labels join)
    df, target, data_source = _load_dataframe(label_from_cfg)

    # Choose features that actually exist
    use_nums = [c for c in NUMERIC_DEFAULT if c in df.columns]
    use_cats = [c for c in CATEG_DEFAULT if c in df.columns]

    # Basic sanity checks
    if target not in df.columns:
        raise SystemExit(f"Label column '{target}' not found after loading data. Aborting.")
    if not use_nums and not use_cats:
        raise SystemExit("No usable features found. Ensure numeric/categorical columns exist.")

    # Train/val split
    X = df[use_nums + use_cats].copy()
    y = df[target].astype(int)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=42
    )

    pre = ColumnTransformer(
        transformers=[
            ("num", "passthrough", use_nums),
            ("cat", _onehot_encoder(), use_cats),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    clf = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        n_jobs=0,
        random_state=42,
        eval_metric="aucpr",
    )

    pipe = Pipeline([("pre", pre), ("clf", clf)])

    # MLflow logging
    mlflow.set_experiment("fraud_stage6_training")
    run_name = f"fraud_candidate_{RUN_TS}"
    with mlflow.start_run(run_name=run_name):
        pipe.fit(X_train, y_train)

        # Validation metrics
        val_proba = pipe.predict_proba(X_val)[:, 1]
        ap = average_precision_score(y_val, val_proba)
        precisions, recalls, thresholds = precision_recall_curve(y_val, val_proba)
        target_recall = 0.90
        f1 = (2 * precisions * recalls) / (precisions + recalls + 1e-9)
        mask = recalls >= target_recall
        best_idx = int(np.argmax(f1[mask])) if mask.any() else int(np.argmax(f1))
        thr = float(thresholds[max(best_idx, 0)]) if len(thresholds) else 0.5

        # Log params/metrics
        mlflow.log_param("data_source", data_source)
        mlflow.log_param("label_column", target)
        mlflow.log_param("use_numeric", ",".join(use_nums))
        mlflow.log_param("use_categorical", ",".join(use_cats))
        mlflow.log_metric("ap_val", float(ap))
        mlflow.log_metric("thr_selected", thr)

        # Save artifacts
        joblib.dump(pipe, CAND_DIR / "xgb_model.joblib")
        json.dump({"numeric": use_nums, "categorical": use_cats}, open(CAND_DIR / "feature_list.json", "w"))
        json.dump({"threshold": thr, "trained_at": RUN_TS}, open(CAND_DIR / "threshold.json", "w"))
        json.dump(
            {
                "run_name": run_name,
                "data_source": data_source,
                "label_column": target,
                "ap_val": float(ap),
                "thr_selected": thr,
                "timestamp": RUN_TS,
            },
            open(CAND_DIR / "training_summary.json", "w"),
            indent=2,
        )

        # Log to MLflow
        mlflow.log_artifact(str(CAND_DIR / "xgb_model.joblib"))
        mlflow.log_artifact(str(CAND_DIR / "feature_list.json"))
        mlflow.log_artifact(str(CAND_DIR / "threshold.json"))
        mlflow.log_artifact(str(CAND_DIR / "training_summary.json"))

    print(f"[OK] Candidate written to: {CAND_DIR}")
    print(f"[OK] MLflow run: {run_name} (experiment: fraud_stage6_training)")


if __name__ == "__main__":
    main()