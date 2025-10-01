# Stage 4 Part A — Credit (Batch Scoring) Progress Log

## Overview
Stage 4 (Part A) focused on implementing **batch portfolio scoring** for the credit module.  
We successfully built the scoring script, produced PD, EL, and segment rollups, and validated outputs with a health check and MLflow logging.

---

## Steps Completed
1. **Scorer script (`score_credit_portfolio.py`)**  
   - Loads latest trained credit model (Stage 3).  
   - Applies timestamp guard (ensures features are newer than raw loans).  
   - Computes PD, EAD, LGD, EL per borrower.  
   - Produces borrower-level PD scores and segment-level rollups.  
   - Logs run into MLflow (after enabling local tracking).

2. **Configuration file (`credit_scoring_config.json`)**  
   - Centralized model/feature paths.  
   - Defined segment keys: `grade`, `state`, `vintage_year`.  
   - Added LGD default and model preference order.

3. **Outputs**  
   - `outputs/scoring/pd_scores_YYYYMMDD.parquet`  
   - `outputs/scoring/segment_rollups_YYYYMMDD.parquet`

4. **Health check (`health_checks_stage4_credit.py`)**  
   - Verified model presence.  
   - Confirmed scoring outputs exist and are recent.  
   - Checked for negative EL values and missing columns.  
   - Added soft warnings for PD outside [0,1] and missing segment keys.

5. **MLflow setup**  
   - Enabled permanent local tracking directory via:  
     ```powershell
     setx MLFLOW_TRACKING_URI "file:///C:/DevProjects/risk_analysis_flagship/mlruns"
     ```
   - Runs are now logged in `mlruns/0`.

---

## Problems Faced and Fixes

### Missing segment columns
- **Problem:** Initial runs failed with  

AssertionError: Missing required column in raw loans: 'grade'
- **Cause:** `loans.csv` lacked the Stage-4 required segmentation fields (`grade`, `state`, `vintage_year`).  
- **Fix:** We manually edited `loans.csv` to include these columns:
- **grade**: values A–G (based on `annual_income / loan_amount` ratio or manual assignment).  
- **state**: valid 2-letter US codes.  
- **vintage_year**: integers in [2000, 2025].

### Feature mismatch with trained model
- **Problem:** After adding new numeric columns, model prediction failed:  
ValueError: The feature names should match those that were passed during fit.
- **Cause:** The scorer was passing extra columns (`loan_amount`, `vintage_year`) not used in training.  
- **Fix:** Patched scorer to align features strictly with `model.feature_names_in_` (or `feature_list.json`). Now it drops unseen columns and orders them correctly.

### SHAP warnings
- **Problem:** SHAP attempted to run by default but failed on the pipeline.  
- **Fix:** Made SHAP opt-in via `ENABLE_SHAP=1`. Now the script runs cleanly by default; SHAP is available on demand.

### MLflow warning
- **Problem:** Warning: `Could not find experiment with ID 0`.  
- **Cause:** No default MLflow tracking URI configured.  
- **Fix:** Added permanent MLflow tracking directory. Now runs are logged without warnings.

---

## Success Criteria Achieved
- ✅ Portfolio scored without errors; borrower PD + EL outputs produced.  
- ✅ Segment rollups computed by grade, state, vintage_year.  
- ✅ Health checks pass locally.  
- ✅ MLflow tracking enabled and logging.  
- ✅ Timestamp guard prevents stale feature use.

---

# Progress Log — Stage 4 Part B (Fraud Detection: Real-Time Scoring API)

## Overview
This stage focused on building a **real-time Fraud Scoring API** using FastAPI, integrating the trained XGBoost model, rule engine, and SHAP explanations from Stage 3. The goal was to expose `/health` and `/score` endpoints, log scoring requests, and verify everything with tests, health checks, and (eventually) CI smoke jobs.

---

## Steps Completed

### 1. Data Schema Alignment
- Verified and updated `fraud_detection_system\data\raw\transactions.csv` to include required fields:
  - `amount`, `account_age_days`, `country`, `device_id`, `hour_of_day`.
- Confirmed compliance with Stage 4 input schema (Pydantic `TransactionIn`).
- Noted that retraining is required if we want the model to use new categorical fields (`country`, `device_id`).

### 2. API Scaffolding
- Created folders:
  - `fraud_detection_system\api\`
  - `fraud_detection_system\api\logs\`
  - `fraud_detection_system\api\tests\`
- Implemented `app.py`:
  - Loads latest fraud model artifacts (`xgb_model.joblib`, `threshold.json`, `feature_list.json`).
  - Loads `rules_v1.yml` for rule-based overrides.
  - Initializes SHAP explainer if available.
  - Defines:
    - `GET /health` → returns model timestamp, rule count, feature count.
    - `POST /score` → accepts JSON transaction, applies rules + model, returns decision object with probability, rule hits, optional top features, latency.
  - Writes request logs in JSONL format under `api\logs\YYYYMMDD.jsonl`.

- Implemented `run_api.py`:
  - Runs Uvicorn with reload enabled.
  - Added `__init__.py` files to make `fraud_detection_system` a proper package.

### 3. VS Code Integration
- Added `.vscode\tasks.json` entry:
  - `"Fraud API (reload)"` task runs the API with one click.

### 4. Debugging & Fixes
- Initial import error (`ModuleNotFoundError: fraud_detection_system`) → fixed by adding `__init__.py` and adjusting `run_api.py`.
- Warning: reload not active when passing live `app` object → fixed by reverting to import string (`fraud_detection_system.api.app:app`) in `uvicorn.run`.
- `/health` initially showed `features_count: 1` because `feature_list.json` was dict-shaped.  
  - Fixed by enhancing loader to merge `numeric_features` + `categorical_features`.

### 5. Testing
- Verified `/health`:
  - Returned correct status, model timestamp, rules_count, features_count.
- Verified `/score`:
  - Sent valid transaction via PowerShell `Invoke-RestMethod`.
  - Response included all expected keys: `decision`, `proba`, `rules_hit`, `top_features` (nullable), `model_timestamp`, `latency_ms`.
- Verified logging:
  - JSONL log files created per day under `api\logs\`.
  - Each entry contains request payload, decision, probability, latency, rules hit, model timestamp.
- Health checks:
  - `shared_env\scripts\health_checks_stage4_fraud_api.py` ran successfully → “✅ Stage 4 fraud API health checks passed”.

### 6. CI/CD (Pending)
- Added draft `fraud-api-smoke` job in `.github/workflows/ci.yml`:
  - Installs dependencies, runs health checks, executes pytest, and pings `/health`.
- Not triggered yet because Stage 4 artifacts are not committed. Plan is to test this once Stage 4 fraud work is complete and ready for push.

---

## Success Criteria Review
- ✅ `/health` returns `model_timestamp`, `rules_count`, `features_count`.
- ✅ `/score` returns `decision`, `proba`, `rules_hit`, `top_features`, `latency_ms`.
- ✅ Per-request JSONL logs written under `api\logs\YYYYMMDD.jsonl`.
- ✅ Health check script prints PASS.
- ⏳ CI job `fraud-api-smoke` not yet executed (waiting for commit/PR).

---

## Notes & Next Steps
- Retraining recommended to include `country` and `device_id` in `feature_list.json` (currently only numeric features are used).
- Consider stubbing `/v1/models` to silence repeated 404s in logs (harmless but noisy).
- Once Stage 4 Part B fraud is finalized, commit the changes on a feature branch and trigger CI to validate `fraud-api-smoke`.
- Stage 4 for Credit Scoring did not yet include an API — only batch scoring pipeline. If desired, we can mirror the Fraud API structure for Credit in a “Stage 4 Part C” or future step for consistency.
