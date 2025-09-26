# Stage 2 — Progress Log (Feature Engineering + Health Checks)
**Project:** Credit Risk Scoring & Fraud Detection  
**Window:** 2025-09-25 → 2025-09-26 (America/Los_Angeles)  
**Owner:** Risk Analytics (you)  
**Status:** ✅ Completed

---

## 1) Objectives
- Build initial **credit** borrower-level features and write to a feature store.
- Build initial **fraud** features for **batch** (user-day, merchant) and **streaming** (per-transaction).
- Add minimal **health checks** to validate outputs.
- (Governance doc created **after** testing, per decision.)

---

## 2) What we built (by system)

### 2.1 Credit Risk — Borrower Features
- **Script:** `credit_scoring_system/scripts/build_features_credit.py`
- **Input:** `credit_scoring_system/data/raw/loans.csv`
- **Output:** `credit_scoring_system/data/featurestore/credit_features.parquet` (CSV fallback supported)
- **Engineered features (borrower granularity):**
  - `income_to_loan_ratio` — annual_income / loan_amount (mean across rows per borrower)
  - `num_past_delinquencies` — max across rows
  - `credit_utilization_pct` — prefers `revol_util` %, else `(revol_bal / total_rev_hi_lim) * 100` (mean)

### 2.2 Fraud Detection — Batch & Streaming
- **Script:** `fraud_detection_system/scripts/build_features_fraud.py`
- **Input:** `fraud_detection_system/data/raw/transactions.csv` (sample created by you)
- **Batch outputs (Parquet):**
  - `fraud_detection_system/data/features_batch/user_daily_velocity.parquet`
    - Includes: `user_txn_count_day`, `user_txn_amount_day`, `device_change_count_day`
  - `fraud_detection_system/data/features_batch/device_change_count_daily.parquet` (same data for discoverability)
  - `fraud_detection_system/data/features_batch/merchant_chargeback_rate.parquet`
- **Streaming output (Parquet):**
  - `fraud_detection_system/data/features_stream/stream_features.parquet`
    - Includes: `rolling_amount_last_1h`, `geo_location_mismatch` (+ ids/timestamps)

---

## 3) Execution record (GUI-first flow)

1. **Created folders**  
   - `credit_scoring_system/data/featurestore/`  
   - `fraud_detection_system/data/features_batch/`  
   - `fraud_detection_system/data/features_stream/`

2. **Added scripts**  
   - Credit: `build_features_credit.py` (schema-tolerant, CSV fallback)  
   - Fraud:  `build_features_fraud.py` (batch + stream, CSV fallback)

3. **Prepared raw data**  
   - Credit: `loans.csv` (fixed header/values)  
   - Fraud:  `transactions.csv` (sample set with multiple users, merchants, devices, countries)

4. **Ran pipelines** (Explorer → Right-click → Run Python File in Terminal)  
   - Credit run: **OK** → wrote `credit_features.parquet`  
   - Fraud run: **initial error, then OK** (see Fixes below) → wrote batch + stream Parquet files

5. **Health checks (Stage 2)**  
   - **Script:** `shared_env/scripts/health_checks_stage2.py`  
   - **Result:** `✅ ALL HEALTH CHECKS PASSED`

6. **Governance (after testing)**  
   - **Doc:** `docs_global/FEATURE_LOG.md` (features + lineage + granularity) — created **after** health checks, per decision.

---

## 4) Issues encountered & fixes

### 4.1 Streaming rolling window error
- **Symptom:** `ValueError: cannot reindex on an axis with duplicate labels` on rolling calc; plus `FutureWarning` about `GroupBy.apply`.
- **Root cause:** The earlier approach used `groupby().apply()` with a manual reset, causing index misalignment on assignment.
- **Fix:** Switched to **time-based** `groupby(user).rolling(window, on=timestamp)[amount].sum()`  
  - Dropped group key index with `reset_index(level=0, drop=True)` for clean alignment.  
  - Eliminated the deprecation warning and assignment error.
- **Commit message used:** `fix(fraud): stable rolling window calc + index-safe stream features`

---

## 5) Validation results (minimal, Stage 2)

### Credit — Borrower
- **Rule:** `income_to_loan_ratio > 0` for non-null rows  
- **Result:** **Pass**

### Fraud — Batch
- **Rules:**  
  - `user_txn_count_day >= 0` — **Pass**  
  - `user_txn_amount_day >= 0` — **Pass**  
  - `merchant_chargeback_rate in [0,1]` — **Pass**

### Fraud — Streaming
- **Rule:** `rolling_amount_last_1h >= 0` for non-null rows — **Pass**

> Health check runner: `shared_env/scripts/health_checks_stage2.py` → **✅ ALL HEALTH CHECKS PASSED**

---

## 6) Artifacts & paths (reference)

- **Credit scripts/data**
  - `credit_scoring_system/scripts/build_features_credit.py`
  - `credit_scoring_system/data/raw/loans.csv`
  - `credit_scoring_system/data/featurestore/credit_features.parquet`

- **Fraud scripts/data**
  - `fraud_detection_system/scripts/build_features_fraud.py`
  - `fraud_detection_system/data/raw/transactions.csv`
  - `fraud_detection_system/data/features_batch/…`
  - `fraud_detection_system/data/features_stream/stream_features.parquet`

- **Shared**
  - `shared_env/scripts/health_checks_stage2.py`
  - `docs_global/FEATURE_LOG.md` (added post-testing)

---

## 7) Decisions & conventions
- **Instruction style:** GUI-first; only use terminal one-liners when unavoidable.  
- **Docs timing:** Governance docs **after** successful runs/tests to avoid churn.  
- **File formats:** Prefer **Parquet**; auto-fallback to CSV if `pyarrow` is missing.  
- **Schema tolerance:** Scripts support common alias columns; non-numeric coerced; infinities → `NaN`.

---

## 8) Commits (messages used)
- `feat(credit): add initial feature engineering pipeline`
- `feat(fraud): add feature engineering pipeline (batch + stream)`
- `fix(fraud): stable rolling window calc + index-safe stream features`
- `chore: add Stage 2 health checks (credit+fraud)`
- `docs: add feature log for credit + fraud Stage 2`

---

## 9) Ready for Stage 3
- **Credit Stage 3:** Baseline model training & tracking (MLflow), feature import wiring.  
- **Fraud Stage 3:** Rules + model baseline, score assembly for decisioning.  
- **Pre-req:** Keep Stage 2 scripts stable; extend health checks as we add features.

