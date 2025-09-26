# FEATURE LOG — Credit Scoring & Fraud Detection (Stage 2)
**Purpose:** Central registry of engineered features, their definitions, inputs, owners, and output datasets.  
**Scope:** Credit Risk (borrower features) and Fraud Detection (batch + streaming features).  
**Last updated:** 2025-09-25

---

## Conventions
- **Granularity** must be explicit (e.g., borrower, user-day, merchant, transaction).
- **Lineage** must reference the upstream script and the raw source dataset(s).
- **Outputs** list the exact path(s) written by pipelines.
- **Deprecation**: mark deprecated features with `~~strikethrough~~` and add a note in the Changelog.

---

## Source Datasets
- **Credit raw**: `credit_scoring_system/data/raw/loans.csv`
- **Fraud raw**: `fraud_detection_system/data/raw/transactions.csv`

---

## CREDIT RISK — Borrower-Level Features
**Upstream script:** `credit_scoring_system/scripts/build_features_credit.py`  
**Output dataset:** `credit_scoring_system/data/featurestore/credit_features.parquet`  
**Granularity:** Borrower (one row per borrower ID)

| Feature name              | Definition & Formula                                                                 | Inputs (typical)                                                                                     | Notes |
|---|---|---|---|
| `income_to_loan_ratio`    | Ratio of borrower annual income to loan amount. If multiple rows per borrower, mean. | `annual_income` (aka `annual_inc`, `income`), `loan_amount` (aka `loan_amnt`, `funded_amnt`, `amount`) | Infinite ratios coerced to `NaN`. |
| `num_past_delinquencies`  | Historical delinquency count; borrower-level **max** across rows.                     | `delinq_2yrs` (aka `total_late_payments`, `past_delinquencies`)                                       | If not present, set `NaN`. |
| `credit_utilization_pct`  | Preferred: parsed `%` from `revol_util`; else `(revol_bal / total_rev_hi_lim) * 100`, borrower-level mean. | `revol_util` or `revol_bal`, `total_rev_hi_lim`                                                       | Non-numeric/inf coerced to `NaN`. |

**Quality/Edge Notes**
- Non-numeric strings and `%` symbols are coerced safely.
- Multiple schema aliases supported (see script).
- Aggregations: mean for ratios/utilization; max for delinquencies.

---

## FRAUD DETECTION — Batch Features
**Upstream script:** `fraud_detection_system/scripts/build_features_fraud.py`  
**Outputs (Parquet):**
- `fraud_detection_system/data/features_batch/user_daily_velocity.parquet` (includes count, amount, device changes)
- `fraud_detection_system/data/features_batch/device_change_count_daily.parquet` (same data, discoverability)
- `fraud_detection_system/data/features_batch/merchant_chargeback_rate.parquet`

**Granularity:** User-Day / Merchant

| Feature name                         | Definition & Formula                                                                                          | Inputs (typical)                                              | Granularity |
|---|---|---|---|
| `user_transaction_velocity_count`    | Number of transactions per user per day.                                                                      | `user_id`, `timestamp`                                        | User-Day |
| `user_transaction_velocity_amount`   | Sum of amounts per user per day.                                                                              | `user_id`, `timestamp`, `amount`                              | User-Day |
| `device_change_count_day`            | Count of device switches within a day per user (successive tx where `device` differs).                         | `user_id`, `timestamp`, `device_id`                           | User-Day |
| `merchant_chargeback_rate`           | `chargeback_count / txn_count` per merchant (overall rate).                                                   | `merchant_id`, `is_chargeback`                                | Merchant |

**Quality/Edge Notes**
- Device change computed on time-sorted transactions per user.
- `is_chargeback` supports 0/1, Y/N, True/False (normalized in script).

---

## FRAUD DETECTION — Streaming Features
**Upstream script:** `fraud_detection_system/scripts/build_features_fraud.py`  
**Output (Parquet):** `fraud_detection_system/data/features_stream/stream_features.parquet`  
**Granularity:** Transaction

| Feature name                | Definition & Formula                                                                                          | Inputs (typical)                            | Granularity |
|---|---|---|---|
| `rolling_amount_last_1h`    | Time-based rolling sum of `amount` over the previous **1 hour** per user (includes current event).            | `user_id`, `timestamp`, `amount`            | Transaction |
| `geo_location_mismatch`     | Boolean flag: current `country` differs from the user’s prior modal country (up to the previous transaction). | `user_id`, `timestamp`, `country`           | Transaction |

**Quality/Edge Notes**
- Rolling window uses `groupby(user).rolling(on=timestamp)`.
- Country modal comparison excludes current row (prior history only).

---

## Ownership
- **Data owner:** Risk Analytics (shared)  
- **Technical owner:** ML/Data Engineering (shared foundations)

---

## Changelog
- **2025-09-25** — Added initial Credit features (`income_to_loan_ratio`, `num_past_delinquencies`, `credit_utilization_pct`) and Fraud features (`user_transaction_velocity_*`, `device_change_count_day`, `merchant_chargeback_rate`, `rolling_amount_last_1h`, `geo_location_mismatch`).
