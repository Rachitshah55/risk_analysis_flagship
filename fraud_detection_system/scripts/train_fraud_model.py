# ===== BEGIN: train_fraud_model.py =====
import os, sys, time, json, joblib, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, roc_auc_score, confusion_matrix
from xgboost import XGBClassifier
import mlflow
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
FRAUD_ROOT = ROOT / "fraud_detection_system"
STREAM_FEATS = FRAUD_ROOT / "data" / "features_stream" / "stream_features.parquet"
RAW_TXN     = FRAUD_ROOT / "data" / "raw" / "transactions.csv"
RULES_YAML  = FRAUD_ROOT / "rules" / "rules_v1.yml"
MODELS_DIR  = FRAUD_ROOT / "models"
ARTIF_DIR   = MODELS_DIR / "artifacts_fraud"
DOCS_CARD   = FRAUD_ROOT / "docs" / "model_cards" / "fraud_model.md"

ARTIF_DIR.mkdir(parents=True, exist_ok=True)
DOCS_CARD.parent.mkdir(parents=True, exist_ok=True)

# Ensure we can import rules_engine from fraud_detection_system/src
SRC_DIR = FRAUD_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
from rules_engine import RulesEngine  # after sys.path patch

def pick_first(df, names):
    for n in names:
        if n in df.columns:
            return n
    raise KeyError(f"Missing any of {names}")

def load_labels(txn: pd.DataFrame) -> pd.Series:
    for c in ["is_fraud", "isFraud", "fraud_flag", "Class", "is_chargeback"]:
        if c in txn.columns:
            # coerce to int safely
            return txn[c].astype(str).str.strip().replace({"True":"1","False":"0"}).astype(float).astype(int)
    raise KeyError("No label column found (expected one of is_fraud/isFraud/fraud_flag/Class).")

def choose_threshold_by_recall(y_true, probs, target_recall=0.90):
    cuts = np.linspace(0.05, 0.95, 19)
    best = (0.5, -1.0, -1.0)
    for t in cuts:
        pred = (probs >= t).astype(int)
        rec = recall_score(y_true, pred, zero_division=0)
        prec = precision_score(y_true, pred, zero_division=0)
        if rec >= target_recall and prec > best[1]:
            best = (t, prec, rec)
    if best[1] < 0:
        f1best, thrbest = -1.0, 0.5
        for t in cuts:
            pred = (probs >= t).astype(int)
            p = precision_score(y_true, pred, zero_division=0)
            r = recall_score(y_true, pred, zero_division=0)
            f1 = 0 if (p+r)==0 else 2*p*r/(p+r)
            if f1 > f1best:
                f1best, thrbest = f1, t
        return float(thrbest)
    return float(best[0])

def plot_cm(y_true, y_pred, out_png):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(4,4))
    ax.imshow(cm, interpolation='nearest')
    ax.set_title('Confusion Matrix')
    for (i,j), v in np.ndenumerate(cm):
        ax.text(j, i, str(v), ha='center', va='center')
    ax.set_xlabel('Predicted'); ax.set_ylabel('Actual')
    fig.tight_layout(); fig.savefig(out_png); plt.close(fig)

def timestamp_guard():
    # Guard 1: features must exist
    if not STREAM_FEATS.exists():
        print("⚠️ Missing stream features. Run build_features_fraud.py first.")
        sys.exit(1)
    # Guard 2: if raw is newer than features → warn and stop (to mimic Credit pattern)
    try:
        if RAW_TXN.exists() and STREAM_FEATS.stat().st_mtime < RAW_TXN.stat().st_mtime:
            print("⚠️ stream_features.parquet is older than transactions.csv → re-run build_features_fraud.py")
            sys.exit(1)
    except Exception:
        pass
    # Guard 3: rules file presence
    if not RULES_YAML.exists():
        print(f"⚠️ Rules file not found at {RULES_YAML}. Create it and retry.")
        sys.exit(1)

def main():
    mlflow.set_experiment("fraud_stage3_model_and_rules")

    timestamp_guard()

    feats = pd.read_parquet(STREAM_FEATS) if STREAM_FEATS.suffix==".parquet" else pd.read_csv(STREAM_FEATS)
    txn = pd.read_csv(RAW_TXN)

    # Join by transaction id
    txn_id = pick_first(txn, ["transaction_id","tx_id","id"])
    if txn_id not in feats.columns and "transaction_id" in feats.columns:
        feats = feats.rename(columns={"transaction_id": txn_id})
    df = feats.merge(txn, on=txn_id, how="inner")

    # --- Normalize post-merge column names (handles _x/_y) and derive rule features
    def pick(df, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    # unify common fields
    ts_col  = pick(df, ["timestamp","timestamp_x","timestamp_y","event_time","event_ts"])
    uid_col = pick(df, ["user_id","user_id_x","user_id_y","customer_id","account_id"])
    amt_col = pick(df, ["amount","amount_x","amount_y","amt"])

    if amt_col and "amount" not in df:
        df["amount"] = df[amt_col]
    if ts_col and "timestamp" not in df:
        df["timestamp"] = df[ts_col]
    if uid_col and "user_id" not in df:
        df["user_id"] = df[uid_col]

    # hour_of_day
    if "hour_of_day" not in df.columns:
        tcol = pick(df, ["timestamp","event_time","event_ts"])
        if tcol:
            df["hour_of_day"] = pd.to_datetime(df[tcol], errors="coerce").dt.hour.fillna(0).astype(int)
        else:
            df["hour_of_day"] = 0

    # account_age_days
    if "account_age_days" not in df.columns:
        ac_col = pick(df, ["account_created_date","acct_created_at","signup_time"])
        tcol  = pick(df, ["timestamp","event_time","event_ts"])
        if ac_col and tcol:
            df["account_age_days"] = (
                pd.to_datetime(df[tcol], errors="coerce") - pd.to_datetime(df[ac_col], errors="coerce")
            ).dt.days.fillna(9999).astype(int)
        else:
            df["account_age_days"] = 9999

    # avg_amount_user
    if "avg_amount_user" not in df.columns:
        ucol = pick(df, ["user_id","customer_id","account_id","uid","userId","user_id_x","user_id_y"])
        if ucol:
            df["avg_amount_user"] = df.groupby(ucol)["amount"].transform("mean").fillna(0)
        else:
            df["avg_amount_user"] = 0.0

    # geo_location_mismatch default
    if "geo_location_mismatch" not in df.columns:
        df["geo_location_mismatch"] = 0


    # Standardize common columns for rules
    if "timestamp" in df.columns:
        df["hour_of_day"] = pd.to_datetime(df["timestamp"]).dt.hour
    if "amount" not in df.columns:
        candidates = [c for c in df.columns if "amount" in c.lower()]
        if candidates:
            df["amount"] = df[candidates[0]]
        else:
            df["amount"] = 0.0
    if "account_age_days" not in df.columns:
        if "account_created_date" in df.columns and "timestamp" in df.columns:
            df["account_age_days"] = (
                pd.to_datetime(df["timestamp"]) - pd.to_datetime(df["account_created_date"])
            ).dt.days.fillna(9999)
        else:
            df["account_age_days"] = 9999
    if "avg_amount_user" not in df.columns and "user_id" in df.columns:
        df["avg_amount_user"] = df.groupby("user_id")["amount"].transform("mean").fillna(0)
    if "geo_location_mismatch" not in df.columns:
        df["geo_location_mismatch"] = 0

    # Labels
    y = load_labels(df)

    # Features: numeric only, drop obvious ids/labels
    drop_cols = {txn_id, "timestamp", "is_fraud","isFraud","fraud_flag","Class"}
    num_cols = [c for c in df.columns if c not in drop_cols and pd.api.types.is_numeric_dtype(df[c])]
    X = df[num_cols].replace([np.inf,-np.inf], np.nan).fillna(0)

    # Stratified split (tiny-data tolerant)
    if len(np.unique(y)) < 2:
        raise ValueError("Only one class present in fraud labels. Need at least one 0 and one 1.")
    test_size = 0.25 if y.value_counts().min() >= 2 else 0.2
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    scale_pos_weight = max(1.0, (y_train.value_counts().get(0,1) / y_train.value_counts().get(1,1)))

    ts = time.strftime("%Y%m%d_%H%M%S")
    run_name = f"fraud_stage3_{ts}"

    with mlflow.start_run(run_name=run_name):
        xgb = XGBClassifier(
            n_estimators=500, max_depth=4, learning_rate=0.07,
            subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
            objective="binary:logistic", tree_method="hist",
            random_state=42, scale_pos_weight=scale_pos_weight
        )
        xgb.fit(X_train, y_train)
        proba = xgb.predict_proba(X_test)[:,1]
        auc = roc_auc_score(y_test, proba)

        thr = choose_threshold_by_recall(y_test, proba, target_recall=0.90)
        pred = (proba >= thr).astype(int)
        prec = precision_score(y_test, pred, zero_division=0)
        rec  = recall_score(y_test, pred, zero_division=0)

        mlflow.log_params({"features_count": len(num_cols), "scale_pos_weight": scale_pos_weight})
        mlflow.log_metrics({"auc": auc, "precision_thr": prec, "recall_thr": rec})

        # Confusion matrix artifact → save in artifacts_fraud
        cm_png = ARTIF_DIR / f"cm_{ts}.png"
        plot_cm(y_test, pred, cm_png)
        mlflow.log_artifact(str(cm_png))

        # Rules on test index
        test_index = X_test.index
        rules_df = df.loc[test_index, [*num_cols, "hour_of_day","amount","account_age_days","avg_amount_user","geo_location_mismatch"]].copy()
        engine = RulesEngine(str(RULES_YAML))
        rules_out = engine.evaluate(rules_df)
        rule_flag = rules_out["rule_flag"].astype(int).values

        # Combined decision: rule OR model
        final_flag = np.where(rule_flag==1, 1, pred)
        prec_c = precision_score(y_test, final_flag, zero_division=0)
        rec_c  = recall_score(y_test, final_flag, zero_division=0)
        mlflow.log_metrics({"precision_combined": prec_c, "recall_combined": rec_c})

        # Persist model + metadata
        out_dir = MODELS_DIR / f"fraud_{ts}"
        out_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(xgb, out_dir / "xgb_model.joblib")
        with open(out_dir / "threshold.json","w", encoding="utf-8") as f:
            json.dump({"threshold": float(thr)}, f, indent=2)
        with open(out_dir / "feature_list.json","w", encoding="utf-8") as f:
            json.dump({"numeric_features": num_cols}, f, indent=2)

        # Model card under FRAUD project folder (not repo root)
        with open(DOCS_CARD,"w",encoding="utf-8") as f:
            f.write("# Fraud Model Card (Stage 3 Baseline)\n\n")
            f.write(json.dumps({
                "model_family":"fraud_txn",
                "timestamp": ts,
                "metrics":{"auc":float(auc),"precision_thr":float(prec),"recall_thr":float(rec),
                           "precision_combined":float(prec_c),"recall_combined":float(rec_c)},
                "notes":"Stage 3 baseline XGB + YAML rules. Threshold chosen for recall. Timestamp guard prevents stale features."
            }, indent=2))
        print(f"✅ Fraud Stage 3 training complete. thr={thr:.3f}")

if __name__ == "__main__":
    main()
# ===== END: train_fraud_model.py =====
