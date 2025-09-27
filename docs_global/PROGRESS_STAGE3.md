# Stage 3 — Progress Log (Credit Models: Logistic + XGBoost)
**Project:** Credit Risk Scoring & Fraud Detection  
**Window:** 2025-09-26 → 2025-09-27 (America/Los_Angeles)  
**Owner:** Risk Analytics (you)  
**Status:** ✅ Completed

---

## 1) Objectives
- Train **baseline credit risk models** using borrower-level features:
  - Logistic Regression (scaled + calibrated)
  - XGBoost baseline
- Track experiments with **MLflow**.
- Persist models, ROC plots, and a **model card**.
- Add a **timestamp guard** (like Stage 2 health checks) to prevent stale features being used after raw data changes.

---

## 2) What we built
- **Script:** `credit_scoring_system/scripts/train_credit_models.py` (full pipeline with fallback logic).
- **Inputs:**
  - Features: `credit_scoring_system/data/featurestore/credit_features.parquet`
  - Raw labels: `credit_scoring_system/data/raw/loans.csv`
- **Outputs:**
  - `credit_scoring_system/models/credit_YYYYmmdd_HHMMSS/`  
    - `logreg_calibrated_or_plain.joblib`  
    - `xgb_model.joblib`  
    - `feature_list.json`
  - `credit_scoring_system/models/artifacts_credit/`  
    - `roc_lr_*.png`  
    - `roc_xgb_*.png`
  - `credit_scoring_system/docs/model_cards/credit_model.md`

---

## 3) Execution record (GUI-first flow)
1. **Created folders**  
   - `credit_scoring_system/models/`  
   - `credit_scoring_system/docs/model_cards/`  

2. **Added script**  
   - `train_credit_models.py` with:
     - Config-aware label detection (`credit_labels_config.json`)
     - Logistic + XGBoost pipelines
     - Calibration fallback for tiny datasets
     - MLflow logging and ROC plots

3. **First runs (errors)**  
   - Error: `"No known default label column found"`  
   - **Fix:** added `loan_status` column manually to `loans.csv`.

4. **Second runs (config errors)**  
   - Error: `"Configured label_column 'LoanStatusText' not found"`  
   - **Fix:** corrected config to `loan_status`.

5. **Third runs (calibration error)**  
   - Error: `"Requesting 3-fold cross-validation but provided less than 3 examples for at least one class"`  
   - **Fix:** added **fallback logic** → if minority class <3, use `cv=2` or uncalibrated LR.

6. **Fourth runs (one-class error)**  
   - Error: `"Only one class present in labels"`  
   - **Fix:** updated `loan_status` with a mix of defaults and non-defaults.

7. **Fifth run (stale features)**  
   - Error: skewed results despite fixes.  
   - **Fix:** re-ran `build_features_credit.py` after updating raw loans.  
   - **Prevention:** added timestamp guard → warns if raw newer than features.

8. **Final run**  
   - Success:
     ```
     Train class counts: {1: 3, 0: 1} | Test class counts: {1: 1, 0: 1}
     ✅ Credit Stage 3 training complete.
     ```

---

## 4) Issues encountered & fixes
- **Missing labels:** added `loan_status` to `loans.csv`.  
- **Config mismatch:** corrected config from `LoanStatusText` → `loan_status`.  
- **Too few samples for calibration:** added cv fallback.  
- **One-class labels:** ensured mix of default + non-default statuses.  
- **Stale featurestore:** re-ran `build_features_credit.py`; added timestamp guard.

---

## 5) Validation results
- Logistic Regression (with calibration fallback):  
  - AUC, KS, Gini logged in MLflow and ROC PNG  
- XGBoost:  
  - AUC, KS logged in MLflow and ROC PNG  
- Artifacts saved under `models/artifacts_credit/`.

---

## 6) Artifacts & paths
- **Scripts:**  
  - `credit_scoring_system/scripts/build_features_credit.py`  
  - `credit_scoring_system/scripts/train_credit_models.py`

- **Data:**  
  - `credit_scoring_system/data/raw/loans.csv` (with `loan_status`)  
  - `credit_scoring_system/data/featurestore/credit_features.parquet` (rebuilt after edit)

- **Models/Artifacts:**  
  - `credit_scoring_system/models/credit_YYYYmmdd_HHMMSS/…`  
  - `credit_scoring_system/models/artifacts_credit/roc_*.png`

- **Docs:**  
  - `credit_scoring_system/docs/model_cards/credit_model.md`  
  - `credit_scoring_system/config/credit_labels_config.json`

---

## 7) Decisions & conventions
- Governance docs created **after successful runs**.  
- Always rebuild features after raw data changes.  
- Labels controlled centrally in `credit_labels_config.json`.  
- Timestamp guard prevents stale features.  
- Calibration adapts: cv=3 if enough, else cv=2, else uncalibrated.

---

# ✅ Progress Log — Stage 3 Part C (Fraud)

## Context
- **Project root:** `C:\DevProjects\risk_analysis_flagship`
- **Subsystem:** Fraud Detection
- **Stage:** 3 (Modeling)
- **Part:** C (Rules Engine + XGBoost + Combined Decision)
- **Goal:** Implement YAML rules, XGBoost baseline fraud model, and a combined decision pipeline with a Timestamp Guard to prevent stale features. Produce a fraud model card for governance.

---

## Steps Completed

### 8) Folder Setup
- Created required directories:
  - `fraud_detection_system\rules\`
  - `fraud_detection_system\models\`
  - `fraud_detection_system\src\`
  - `fraud_detection_system\docs\model_cards\`
  - `fraud_detection_system\models\artifacts_fraud\`

### 9) Rules Definition
- Added `fraud_detection_system\rules\rules_v1.yml`
- Contains three baseline rules:
  1. **High Amount, New Account** — flags large transactions on new accounts.  
  2. **Velocity Spike** — flags spending >3× user’s rolling average.  
  3. **Cross-Border at Odd Hours** — marks suspicious cross-border activity during early hours.

### 10) Rules Engine
- Implemented `fraud_detection_system\src\rules_engine.py`.
- Loads YAML rules and evaluates conditions against transaction DataFrames.
- Produces `rule_flag` (hard flag) and `rule_review` (soft review).

### 11) Training Script
- Added `fraud_detection_system\scripts\train_fraud_model.py`:
  - Integrates rules engine with ML (XGBoost).
  - Timestamp Guard implemented:
    - Ensures `stream_features.parquet` exists.
    - Stops if it is older than `transactions.csv`.
    - Checks rules file presence.
  - Trains XGBoost with stratified split, class balancing, and threshold tuned for **recall ≥ 0.9**.
  - Generates metrics: AUC, precision, recall, combined rules+model performance.
  - Saves model, threshold, and feature list to versioned folder.
  - Exports confusion matrix PNG to `models/artifacts_fraud`.
  - Writes governance **model card** under `docs/model_cards\fraud_model.md`.

### Fixes Applied During Execution
- **Label column mismatch:** Added support for `is_chargeback` in `load_labels()` (your dataset uses this column).  
- **MLflow metric naming:** Replaced invalid keys (`precision@thr`, `recall@thr`) with `precision_thr`, `recall_thr`.  
- **Merge suffix issue:** Normalized `_x/_y` column variants (e.g., `timestamp_x`, `user_id_y`) so derived features (`hour_of_day`, `avg_amount_user`) are always created.

### 12) Execution
- Ran `build_features_fraud.py` proactively:
  - Batch and streaming features successfully recomputed and written.
- Ran `train_fraud_model.py`:
  - ✅ Training completed with no errors.
  - Output printed:  
    ```
    ✅ Fraud Stage 3 training complete. thr=0.100
    ```

---

## Outputs Generated
- **Model artifacts:**
  - `fraud_detection_system\models\fraud_YYYYmmdd_HHMMSS\`
    - `xgb_model.joblib`
    - `threshold.json`
    - `feature_list.json`
- **Visualization:**
  - `fraud_detection_system\models\artifacts_fraud\cm_*.png`
- **Model Card:**
  - `fraud_detection_system\docs\model_cards\fraud_model.md`

---

## Status
- ✅ Stage 3 Part C (Fraud) completed successfully.
- Fraud baseline system now combines:
  - **YAML rules** (interpretable guardrails).
  - **XGBoost classifier** (ML baseline).
  - **Combined decision** (rule OR model).  
- Timestamp Guard protects against stale features.  
- Governance artifacts (model card, metrics, confusion matrix) are in place.

---
