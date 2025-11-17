# ARCHITECTURE — Credit + Fraud Risk Analytics Platform

This document explains **how the system is wired**, not just what models exist.

---

## 1. High-level system view

```text
                +----------------------+
                |  docs_site (static)  |
                |  Cloudflare + local  |
                +----------+-----------+
                           |
                           | HTTP (hosted: mock; local: gateway)
                           v
                 +---------+----------+
                 |  API Gateway (8000)|
                 |  shared_env.api_...|
                 +----+-----------+---+
                      |           |
          HTTP 8002   |           |  HTTP 8001
                      v           v
       +--------------+--+     +--+----------------+
       | Credit API      |     | Fraud API         |
       | FastAPI/Uvicorn |     | FastAPI/Uvicorn   |
       +---------+-------+     +---------+---------+
                 |                       |
                 | batch                 | logs + batch
                 v                       v
   +-------------+-------------+   +-----+----------------------+
   | credit_scoring_system     |   | fraud_detection_system     |
   | features, models, reports |   | features, models, rules    |
   +-------------+-------------+   +--------------+-------------+
                 |                               |
                 | daily artifacts               | daily artifacts
                 v                               v
          +------+-------------------------------+------+
          |           docs_global (local only)          |
          | monitoring, reports, audits, runbooks      |
          +------+------------------+------------------+
                 |                  |
                 | DVC + MLflow     | Tableau / BI
                 v                  v
       +---------+------+   +-------+----------------+
       |   _dvc_remote  |   | docs_global\bi\...     |
       +----------------+   +------------------------+
```

Key principles:

- **Credit** and **fraud** are separate subsystems but share automation, monitoring, and governance.
- **docs_site** is the recruiter-facing frontend; it never talks directly to model services in hosted mode.
- **shared_env** is the “operations brain” of the project.

---

## 2. Credit subsystem

### 2.1. Data & features

- Source: Kaggle credit dataset (e.g. `data\kaggle\credit\cs-training.csv` — gitignored)
- Features stored under:

  - `credit_scoring_system\data\featurestore\credit_features.parquet` (exact filename may vary)

- Typical features:
  - Delinquency counts
  - Utilization ratios
  - Income, age, etc.

### 2.2. Model training (Stage 3)

- Training script (pattern):

  - `credit_scoring_system\scripts\train_credit_model.py`
- Logs metrics to MLflow:

  - Experiment: `credit_stage3_training`
- Models saved under:

  - `credit_scoring_system\models\credit_YYYYMMDD_HHMMSS\`
- Model card:

  - `docs\model_cards\credit_model.md` (also included in audit pack)

### 2.3. Batch scoring (Stage 4)

- Script:

  - `credit_scoring_system\scripts\score_credit_portfolio.py`
- Inputs:
  - Latest featurestore parquet
  - Active PROD model
- Outputs:

  - `credit_scoring_system\outputs\scoring\pd_scores_YYYYMMDD.parquet`

- MLflow experiment:

  - `credit_stage4_scoring`

This is the backbone for downstream reporting and drift monitoring.

### 2.4. Monitoring (Stage 5)

- Script:

  - `shared_env\monitoring\monitor_credit_drift.py`

Responsibilities:

- Load two most recent scoring parquet files
- Normalize PD column to `pd`
- Compute PSI and calibration curves
- Write:

  - `docs_global\monitoring\credit\YYYY-MM\drift_report.html`
  - `docs_global\monitoring\credit\YYYY-MM\drift_summary.csv`
  - `docs_global\monitoring\credit\YYYY-MM\alert.txt` (if PSI ≥ threshold)

Also logs a run in:

- MLflow experiment `credit_stage5_monitoring`

### 2.5. Reporting (Stage 6)

Daily reporting:

- Notebook template:

  - `credit_scoring_system\reports\templates\credit_daily_report.ipynb`
- Renderer / runner:

  - `credit_scoring_system\reports\render_credit_daily_report.py`  
    (wrapped by orchestration)

Outputs (per day):

- `docs_global\reports\credit\YYYY-MM-DD\credit_daily_report.html`
- `docs_global\reports\credit\YYYY-MM-DD\kpis.json`

Monthly roll-up:

- Script:

  - `credit_scoring_system\reports\rollup_month_credit_reports.py`

Outputs:

- `docs_global\reports\credit\YYYY-MM\credit_monthly_summary.html`

MLflow experiments:

- `credit_stage6_daily_reporting`
- `credit_stage6_monthly_rollup`

### 2.6. Orchestration & flows (Stage 7–8)

Main flows:

- `shared_env\orchestration\flows\credit_daily_flow.py`
  - Runs Stage 5 → Stage 4 → Stage 6
  - Calls BI export at the end
- `shared_env\orchestration\flows\monthly_credit_rollup_flow.py`
  - Runs EOM roll-up and verifies outputs

Scheduler plan:

- `Credit Daily` at 08:00
- `Credit EOM Roll-up` on the last day at 23:00

XML exports live under:

- `docs_global\runbooks\scheduler_exports\`

---

## 3. Fraud subsystem

### 3.1. Data & features

- Source: Kaggle fraud dataset (e.g. `data\kaggle\fraud\fraudTrain.csv` — gitignored)
- Features:

  - `fraud_detection_system\data\features_batch\...`
  - `fraud_detection_system\data\features_stream\...`

Batch features capture user/merchant history; streaming features capture short-term behavior and device changes.

### 3.2. Model + rules (Stages 3–4)

- Training script:

  - `fraud_detection_system\scripts\train_fraud_candidate.py`
- Models saved under:

  - `fraud_detection_system\models\CAND_YYYYMMDD\`
- PROD pointer:

  - `fraud_detection_system\models\PROD_POINTER.txt` (path to chosen CAND)
- Rules:

  - `fraud_detection_system\rules\rules_v1.yml`
  - `fraud_detection_system\rules\CHANGELOG.md` (governed)

Model card:

- `docs\model_cards\fraud_model.md`

### 3.3. Fraud API (Stage 4)

- Entry script:

  - `fraud_detection_system\api\run_api.py`
- Endpoints:

  - `GET /health` – readiness, model path, basic config
  - `GET /docs` – OpenAPI UI
  - `POST /score` – transaction JSON → fraud score + flags

Logs:

- `fraud_detection_system\api\logs\YYYYMMDD.jsonl` (current PROD)
- `fraud_detection_system\api\logs\YYYYMMDD_shadow.jsonl` (shadow candidate)

These logs feed A/B evaluation and daily monitoring.

### 3.4. A/B evaluation & promotions (Stage 6)

Script:

- `fraud_detection_system\analysis\evaluate_ab_and_promote.py`

Responsibilities:

- Compare PROD vs candidate:
  - Precision / recall / FPR
  - Latency
  - Volume, approval rates
- Write:

  - `docs_global\reports\fraud\ab_tests\YYYY-MM\ab_summary_YYYYMMDD.csv`
  - `docs_global\reports\fraud\ab_tests\YYYY-MM\ab_summary_YYYYMMDD.html`
- Update:

  - `fraud_detection_system\models\PROD_POINTER.txt`
  - `docs_global\releases\fraud_PROD_YYYYMMDD.txt` (breadcrumb)

Promotion runbooks:

- `docs_global\runbooks\fraud_ab_promotion.md`
- `docs_global\runbooks\rollback_fraud_prod.md`

### 3.5. Monitoring (Stages 5–7)

Daily monitor:

- `shared_env\monitoring\monitor_fraud_api_logs.py`

Outputs (per day):

- `docs_global\monitoring\fraud\YYYY-MM-DD\summary.csv`
- `docs_global\monitoring\fraud\YYYY-MM-DD\summary.json`
- `docs_global\monitoring\fraud\YYYY-MM-DD\raw_current.csv`
- `docs_global\monitoring\fraud\YYYY-MM-DD\drift_report.html`

Monthly roll-up (Stage 7):

- `fraud_detection_system\reports\rollup_month_fraud_reports.py`
- Outputs:
  - `docs_global\reports\fraud\YYYY-MM\fraud_monthly_summary.html`
  - `docs_global\reports\fraud\YYYY-MM\monthly_kpis.json`

MLflow experiments (examples):

- `fraud_stage5_monitoring`
- `fraud_stage7_monthly_rollup`

---

## 4. shared_env — orchestration, monitoring, and ops

Key subfolders:

- `shared_env\orchestration\flows\`
  - `credit_daily_flow.py`
  - `fraud_daily_flow.py`
  - `monthly_credit_rollup_flow.py`
- `shared_env\monitoring\`
  - `monitor_credit_drift.py`
  - `monitor_fraud_api_logs.py`
  - `alert_bridge.py`
- `shared_env\contracts\`
  - `validate_credit_outputs.py`
  - `validate_fraud_logs.py`
- `shared_env\ci\`
  - `governance_gate.py`
- `shared_env\backup\`
  - `nightly_snapshot.py` (DVC push + zipped reports)
- `shared_env\ops\`
  - `tasks_export.ps1`
  - `tasks_import.ps1`

These modules are shared between credit and fraud and form the operational backbone.

---

## 5. docs_site — static showroom

Location:

- `docs_site\`

Key pieces:

- HTML/CSS/JS components for Home, Credit, Fraud, Ops
- Demo CSVs under:
  - `docs_site\demo_data\credit\kpis_daily.csv`
  - `docs_site\demo_data\fraud\kpis_daily.csv`
  - `docs_site\demo_data\fraud\metrics_daily.csv`
- Config:

  - `docs_site\config.json`
    - `"mode": "hosted" | "local"`
    - `"apiBase": "http://127.0.0.1:8000"`
    - `"useMock": true | false`

Hosted on Cloudflare Pages:

- Project root: repo root
- Output directory: `docs_site`
- No build step (pure static)

Local mode:

- Served via `python -m http.server 8010`
- When `"mode": "local"` and `"useMock": false`, buttons call the gateway.

---

## 6. docs_global — local-only evidence

This folder is **intentionally gitignored** and used as the “evidence warehouse”:

- `docs_global\monitoring\credit\...`
- `docs_global\monitoring\fraud\...`
- `docs_global\reports\credit\...`
- `docs_global\reports\fraud\...`
- `docs_global\audits\YYYY-MM-DD\...`
- `docs_global\runbooks\...`
- `docs_global\bi\tableau\Risk_Analytics_seed.twbx`
- `docs_global\config\PROJECT_FACTS_LOCK.md`

It is not required to open the repo, but it is **essential** to demonstrate:

- Steady-state operations
- Historical monitoring
- Governance & sign-off evidence

See `docs/OPS_AND_GOVERNANCE.md` for how these pieces relate to CI, audit packs, and runbooks.

---

## 7. DVC, MLflow, and backups

- **MLflow:**
  - Backend: local `mlruns/` directory
  - UI: `mlflow ui --backend-store-uri mlruns --port 5000`

- **DVC:**
  - Initialized at repo root
  - Local remote: `_dvc_remote\`
  - Used to version:
    - Critical input data (Kaggle snapshots)
    - Key outputs (reports/monitoring)

- **Backups:**
  - `shared_env\backup\nightly_snapshot.py`:
    - Runs `dvc push`
    - Zips daily/EOM reports under `docs_global\reports\**`

Nightly job can be wired into Windows Task Scheduler if desired.

---

## 8. CI and governance overview

CI workflows (see `.github\workflows\ci.yml`):

- `reporting-smoke` — checks daily/monthly flows + report generation (lightweight)
- `unit-min` — minimal unit tests
- `data-contract-smoke` — runs output validators
- `api-http-integration` — HTTP-level API checks (non-blocking)
- `fraud-api-smoke` — focused readiness probe on fraud API

Governance gate:

- `shared_env\ci\governance_gate.py`:
  - Ensures model cards and rules changelog changed when PROD pointer changes
  - Ensures audit pack and evidence exist for releases

See `docs/OPS_AND_GOVERNANCE.md` for details.
