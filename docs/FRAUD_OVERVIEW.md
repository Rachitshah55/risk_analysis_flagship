# FRAUD_OVERVIEW — Fraud Detection System

This document focuses on the **fraud half** of the platform: data, model + rules, streaming logs, and A/B promotion logic.

---

## 1. Business problem

Goal:

- Detect suspicious transactions in near real-time
- Combine **ML scores** with **business rules**
- Keep **false positives** under control while catching as much fraud as possible
- Monitor model performance and latency daily

This mirrors typical card/transaction fraud setups used by banks and payments companies.

---

## 2. Data and feature pipelines

### 2.1. Source dataset

- Kaggle **credit card transactions fraud** dataset:
  - Stored under: `data\kaggle\fraud\fraudTrain.csv` (gitignored)
  - Contains transaction-level fields and fraud labels

### 2.2. Features

Batch features:

- Stored under: `fraud_detection_system\data\features_batch\...`
- Capture:
  - Historical user behavior
  - Merchant chargeback rates
  - Geographic / device patterns

Streaming features:

- Stored under: `fraud_detection_system\data\features_stream\...`
- Capture:
  - Short-term velocity (1h volume/amount)
  - Device changes
  - IP / location shifts

These feed the training and scoring processes.

---

## 3. Model + rules engine

### 3.1. Candidate model training

Script:

- `fraud_detection_system\scripts\train_fraud_candidate.py`

Outputs:

- Model directories:
  - `fraud_detection_system\models\CAND_YYYYMMDD\`
- MLflow:
  - Experiment: `fraud_stage3_training` (name pattern may vary)
- Metrics:
  - ROC-AUC, precision, recall, FPR
  - Latency metrics where applicable

### 3.2. Rules

File:

- `fraud_detection_system\rules\rules_v1.yml`

Content (conceptually):

- Threshold rules:
  - large amount + young account age
  - risky merchant categories
  - unusual device / country jumps
- Risk flags and actions:
  - block, review, step-up authentication

Changes tracked in:

- `fraud_detection_system\rules\CHANGELOG.md`

Rules + model outputs combine into a final decision.

### 3.3. PROD pointer and model card

- Active model path:

  - `fraud_detection_system\models\PROD_POINTER.txt` (single-line path)
- Releases logged via:

  - `docs_global\releases\fraud_PROD_YYYYMMDD.txt`
- Model card:

  - `docs\model_cards\fraud_model.md`

Governance ensures model card and rules changelog are updated on PROD swaps.

---

## 4. Fraud API

Script:

- `fraud_detection_system\api\run_api.py`

Exposes:

- `GET /health` — shows service status, model path, basic config
- `GET /docs` — OpenAPI UI
- `POST /score` — transaction → JSON result

Behavior:

- Loads model pointed by `PROD_POINTER.txt`
- Applies rules from `rules_v1.yml`
- Returns:
  - model_score
  - decision (fraud/not)
  - rule hits / reasons

Logs:

- `fraud_detection_system\api\logs\YYYYMMDD.jsonl` — current PROD
- `fraud_detection_system\api\logs\YYYYMMDD_shadow.jsonl` — candidate shadow

These logs are the main input to downstream monitoring and A/B evaluation.

---

## 5. A/B testing and model promotion

Script:

- `fraud_detection_system\analysis\evaluate_ab_and_promote.py`

Workflow:

1. Read logs for PROD and candidate:
   - `logs\YYYYMMDD.jsonl`
   - `logs\YYYYMMDD_shadow.jsonl`
2. Compute KPIs:
   - Precision, recall, FPR
   - Latency metrics
   - Share of transactions flagged
3. Generate report:
   - `docs_global\reports\fraud\ab_tests\YYYY-MM\ab_summary_YYYYMMDD.csv`
   - `docs_global\reports\fraud\ab_tests\YYYY-MM\ab_summary_YYYYMMDD.html`
4. When candidate passes thresholds:
   - Update `PROD_POINTER.txt`
   - Write release breadcrumb:
     - `docs_global\releases\fraud_PROD_YYYYMMDD.txt`
   - Append pointer-only entry + smoke evidence to:
     - `docs\model_cards\fraud_model.md`
     - `fraud_detection_system\rules\CHANGELOG.md` (if rules changed)

Runbooks guide the human decision:

- `docs_global\runbooks\fraud_ab_promotion.md`
- `docs_global\runbooks\rollback_fraud_prod.md`

---

## 6. Monitoring and reporting

### 6.1. Daily monitoring (Stage 5–6)

Script:

- `shared_env\monitoring\monitor_fraud_api_logs.py`

Responsibilities:

- Parse daily logs (PROD + shadow)
- Compute:
  - Volume and fraud ratio
  - Precision/recall (if labels available)
  - Latency distribution
- Build drift report on key features

Outputs:

- `docs_global\monitoring\fraud\YYYY-MM-DD\summary.csv`
- `docs_global\monitoring\fraud\YYYY-MM-DD\summary.json`
- `docs_global\monitoring\fraud\YYYY-MM-DD\raw_current.csv`
- `docs_global\monitoring\fraud\YYYY-MM-DD\drift_report.html`

### 6.2. Monthly roll-up (Stage 7)

Script:

- `fraud_detection_system\reports\rollup_month_fraud_reports.py`

Outputs:

- `docs_global\reports\fraud\YYYY-MM\fraud_monthly_summary.html`
- `docs_global\reports\fraud\YYYY-MM\monthly_kpis.json`

MLflow:

- Experiment: `fraud_stage7_monthly_rollup`
- Artifacts:
  - Summary HTML
  - monthly_kpis.json

---

## 7. Orchestration and flows

### 7.1. Daily fraud flow

Flow:

- `shared_env\orchestration\flows\fraud_daily_flow.py`

Sequence:

1. Ensure fraud API ran and logs are present
2. Run `monitor_fraud_api_logs.py`
3. Export BI CSVs for Tableau
4. Optionally notify via alert bridge

Triggered via:

- VS Code task: **Orch: Fraud Daily Flow (Stage 5→7)**
- Windows Task Scheduler: **Fraud Detect Daily** (08:05, after credit)

### 7.2. Integration with docs_site

When running local demo:

- Fraud API listens on 8001
- Gateway (8000) proxies `/score` calls to the fraud API
- docs_site (8010) calls gateway when config is:

  ```json
  {
    "mode": "local",
    "apiBase": "http://127.0.0.1:8000",
    "useMock": false
  }
  ```

The **Fraud** page’s **“Score via API (local only)”** button sends a sample transaction through the full path and displays live JSON response.

---

## 8. How this maps to real-world teams

A fraud or payments team would see this as:

- A reference for **ML + rules** integrated into a scoring API
- A blueprint for **shadow deployment + A/B testing**
- A basic but realistic **monitoring framework** driven by API logs
- Governance practices around:
  - Rules changes
  - Model promotion
  - Audit evidence for on-call / compliance

For demos, show:

- Fraud API `/docs` and `/health`
- Daily monitoring outputs in `docs_global\monitoring\fraud\...`
- A/B summary HTML
- Model card and rules changelog entries for a promotion
