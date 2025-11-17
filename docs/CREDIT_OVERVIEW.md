# CREDIT_OVERVIEW — Credit Risk Scoring System

This document explains the **credit half** of the platform: business goal, dataset, modeling choices, and daily operations.

---

## 1. Business problem

We want to estimate **default risk** for individual borrowers and roll that into **Expected Loss (EL)** at portfolio and segment levels.

Objectives:

- Score each account with a **Probability of Default (PD)**
- Compute **Expected Loss = PD × LGD × EAD**
- Track risk trends with **daily HTML reports** and **EOM roll-ups**
- Ensure the model is **monitored, explainable, and auditable**

This mirrors real banking use cases (IFRS9/CECL-style reporting) but uses open Kaggle data.

---

## 2. Data and features

### 2.1. Source dataset

- Kaggle **“Give Me Some Credit”**-style dataset:
  - Stored under: `data\kaggle\credit\cs-training.csv` (gitignored)
  - Contains borrower-level variables and default labels

### 2.2. Raw to featurestore

Pipeline (simplified):

- Raw CSV → validation → transformation → featurestore:

Typical location:

- `credit_scoring_system\data\featurestore\credit_features.parquet`

Example feature categories:

- Delinquency metrics (past due counts)
- Utilization ratios
- Income and debt levels
- Age, employment proxies, etc.

---

## 3. Model design

### 3.1. Base model

- Algorithm: Logistic regression and/or XGBoost
- Goal: Calibrated PD for each loan

Training script (pattern):

- `credit_scoring_system\scripts\train_credit_model.py`

Outputs:

- Model artifacts under:
  - `credit_scoring_system\models\credit_YYYYMMDD_HHMMSS\`
- Logged to MLflow:
  - Experiment: `credit_stage3_training`

### 3.2. Model card

Public model card lives at:

- `docs\model_cards\credit_model.md`

Contains:

- Model objective, dataset, and timeframe
- Key features and their roles
- Training metrics (ROC-AUC, Brier score, calibration plots)
- Limitations and risk notes
- Release history (linking to audit pack entries)

---

## 4. Scoring & Expected Loss

### 4.1. Batch scoring (Stage 4)

Script:

- `credit_scoring_system\scripts\score_credit_portfolio.py`

Responsibilities:

- Load featurestore parquet and PROD model
- Score each account with PD
- Optionally compute EL using LGD/EAD assumptions

Output:

- `credit_scoring_system\outputs\scoring\pd_scores_YYYYMMDD.parquet`

MLflow:

- Experiment: `credit_stage4_scoring`
- Logs: metrics (e.g. default rate, AUC), artifact samples

### 4.2. Model promotion / PROD pointer

- PROD model path is referenced by:
  - Credit API (port 8002)
  - Scoring script (Stage 4)
- PROD updates are:
  - Logged in MLflow
  - Reflected in model card (`docs\model_cards\credit_model.md`)
  - Included in audit pack under `docs_global\audits\YYYY-MM-DD\credit\credit_model.md`

Governance details are in `docs/OPS_AND_GOVERNANCE.md`.

---

## 5. Monitoring (Stage 5)

### 5.1. Drift & calibration

Script:

- `shared_env\monitoring\monitor_credit_drift.py`

Key features:

- Compares two most recent `pd_scores_*.parquet`
- Normalizes PD column name to `pd`
- Computes PSI for selected numeric features and PD
- Builds calibration curves when labels are available

Outputs:

- `docs_global\monitoring\credit\YYYY-MM\drift_report.html`
- `docs_global\monitoring\credit\YYYY-MM\drift_summary.csv`
- `docs_global\monitoring\credit\YYYY-MM\dropped_columns.csv`
- `docs_global\monitoring\credit\YYYY-MM\alert.txt` (when PSI ≥ threshold)

MLflow:

- Experiment: `credit_stage5_monitoring`

### 5.2. Alerting

- High PSI values can trigger alerts via `alert_bridge.py` at the end of flows.
- Alert thresholds are configured via `.env` and severity rules.

See `docs/OPS_AND_GOVERNANCE.md` for alert policy.

---

## 6. Reporting (Stage 6)

### 6.1. Daily HTML report

Pipeline:

- Uses Stage 4 output and Stage 5 monitor outputs
- Template notebook:
  - `credit_scoring_system\reports\templates\credit_daily_report.ipynb`
- Render script:
  - `credit_scoring_system\reports\render_credit_daily_report.py` (wrapped via flow)

Outputs:

- `docs_global\reports\credit\YYYY-MM-DD\credit_daily_report.html`
- `docs_global\reports\credit\YYYY-MM-DD\kpis.json`

Includes:

- PD distribution, default rate, bad rate by segment
- Top features (importance / SHAP-style summary)
- Portfolio metrics (EL by segment, delinquency trends)

### 6.2. Monthly roll-up

Script:

- `credit_scoring_system\reports\rollup_month_credit_reports.py`

Outputs:

- `docs_global\reports\credit\YYYY-MM\credit_monthly_summary.html`

Content:

- Aggregated KPIs (e.g. average PD, EL, NPL rate)
- Trend charts for key metrics
- Links to daily reports for the month

---

## 7. Operations & orchestration

### 7.1. Daily credit flow

Flow:

- `shared_env\orchestration\flows\credit_daily_flow.py`

Sequence:

1. Run drift monitoring (`monitor_credit_drift.py`)
2. Run portfolio scoring (`score_credit_portfolio.py`)
3. Render daily report (Stage 6)
4. Export BI CSVs
5. Optionally call alert bridge

Controlled via:

- VS Code task: **Orch: Credit Daily Flow (Stage 5→4→6)**
- Windows Task Scheduler: **Credit Daily** (08:00)

### 7.2. Monthly EOM flow

Flow:

- `shared_env\orchestration\flows\monthly_credit_rollup_flow.py`

Runs:

- `rollup_month_credit_reports.py`
- Optional BI export and alerts

Scheduled:

- **Credit EOM Roll-up** at 23:00 on last day of month (XML in `docs_global\runbooks\scheduler_exports\`)

---

## 8. How this maps to real-world teams

A typical credit risk team would see this as:

- A **sandbox** for PD/EL modeling
- A **template** for adding new portfolios (e.g. auto, cards)
- A **reference implementation** for:
  - Daily reporting
  - Monitoring with Evidently
  - Governance (model cards, audit packs, CI gate)
  - Simple but sane orchestration

For interview/demo purposes, you can show:

- Daily HTML report in the browser
- Drift report in `docs_global\monitoring\credit\...`
- MLflow experiment summaries
- Model card + audit pack entry for the credit model
