# Risk Analytics Flagship — Credit Risk Scoring & Fraud Detection

End-to-end **credit risk** and **transaction fraud** platform designed to look like a small real-world risk team’s stack:

- Daily credit portfolio scoring + PD/EL reporting
- Batch + streaming fraud scoring via ML model + rules
- Monitoring with drift, KPIs, and HTML reports
- CI + governance gate, audit packs, and Tableau seed
- Hosted static showroom + local live-API demo

[**Project website**](https://risk-analysis-flagship.pages.dev/)
---

## 1. What this project demonstrates

For a **credit / fraud analytics team**, this repo shows:

- **Credit**
  - Probability of Default (PD) model for loan-level risk
  - Expected Loss (EL) rollups (PD × LGD × EAD)
  - Daily HTML portfolio reports with KPIs and charts
  - Drift + calibration monitoring with Evidently
- **Fraud Detection**
  - Batch + streaming feature pipelines
  - Fraud model + YAML rule engine (rules_v1.yml)
  - Real-time scoring API (`/score`) with JSON output
  - Daily KPI and latency monitoring from API logs
  - A/B evaluation + PROD pointer management
- **Shared Automation**
  - Orchestrated daily flows (credit + fraud)
  - Windows Task Scheduler exports for daily/EOM jobs
  - Alert bridge (Slack + Gmail API/SMTP via `.env`)
  - DVC + MLflow + audit pack for reproducibility
  - Tableau seed workbook bound to project outputs

Built and tested end-to-end on **Windows + Python 3.13**.

---

## 2. Live demo 

### 2.1 Hosted showroom (Cloudflare Pages)

Static docs_site, safe for recruiters:

 [**Risk Analysis Flagship**](https://risk-analysis-flagship.pages.dev/)
 
 It Uses **pre-aggregated Kaggle-based CSVs** only:
  - [credit\kpis_daily.csv](docs_site/demo_data/credit/kpis_daily.csv)
  - [fraud\kpis_daily.csv](docs_site/demo_data/fraud/kpis_daily.csv)
  - [fraud\metrics_daily.csv](docs_site/demo_data/fraud/metrics_daily.csv)


The hosted demo shows:

- Home view with overall status + “Demo Snapshot” window
- Credit page with portfolio KPIs & charts
- Fraud page with detection KPIs & latency
- Ops view with server/flows explainer cards

### 2.2. Tableau dashboards (recommended BI view)

Primary BI view for this project:

[**Risk Analytics — Credit & Fraud KPIs (Tableau Public)**](https://public.tableau.com/views/DailyRiskCommandCenterCreditFraud/RiskCommandCenter?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)  
  

The Tableau dashboard is bound to the same CSV outputs used by the showroom and displays:

- Daily KPIs for credit and fraud  
- Segment breakdowns and trend views  
- Quick visual summary of PD/EL movement and fraud detection performance  

Locally, a **seed Tableau workbook** is maintained as `Risk_Analytics_seed.twbx` under `docs_global/bi/tableau/` (local, gitignored) to rebuild or extend dashboards directly from raw project outputs.


### 2.3 Local live-API demo (for interviews)

Locally you can switch docs_site into **live API mode**:

- Credit API on **8002**
- Fraud API on **8001**
- Gateway on **8000** (`shared_env.api_gateway`)
- Static server for docs_site on **8010**

Use:

- [LOCAL_DEMO_GUIDE.md](LOCAL_DEMO_GUIDE.md) — step-by-step “interview script”
- [TASKS_GUIDE.md](TASKS_GUIDE.md) — how to start flows + APIs cleanly

Hosted demo stays in `{"mode": "hosted", "useMock": true}` for safety; local demo uses `{"mode": "local", "useMock": false}` and sends actual HTTP requests.

---

## 3. Quickstart (local, minimal)

### 3.1. Clone & environment

```bash
# From PowerShell in your projects folder
git clone <your-repo-url> C:\DevProjects\risk_analysis_flagship
cd C:\DevProjects\risk_analysis_flagship

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
# For strict reproducibility / CI: pip install -r requirements.lock
```

### 3.2. Run a quick credit daily chain

From repo root with venv active:

```bash
python shared_env\orchestration\flows\credit_daily_flow.py
```

This will:

- Run credit drift monitor (Stage 5)
- Run credit portfolio scoring (Stage 4)
- Render daily HTML report (Stage 6)
- Export BI-friendly CSVs for Tableau

sample outputs (checked into the repo for GitHub view):

- [pd_scores_YYYYMMDD.parquet](credit_scoring_system/outputs/scoring/pd_scores_20251116.parquet)
- [drift_report.html](credit_scoring_system\sample_outputs\credit\monitoring\2025-12-05\drift_report.html)
- [credit_daily_report.html](credit_scoring_system\sample_outputs\credit\reports\2025-12-05\credit_daily_report.html)

Open the latest daily report in your browser (or via VS Code task).

### 3.3. Run fraud daily chain

```bash
python shared_env\orchestration\flows\fraud_daily_flow.py
```

This will:

- Parse latest fraud API logs
- Write daily monitoring outputs
- Render a daily fraud HTML report
- Export BI-friendly CSVs

⚠️ Important: All real runtime outputs live under docs_global/....
That directory is gitignored on purpose, so you won’t see those files
on GitHub. The paths below describe what happens locally; a static sample
is also checked into fraud_detection_system/sample_outputs/... for
reviewers.


sample outputs (checked into the repo for GitHub view):

- [drift_summary.csv](fraud_detection_system\sample_outputs\fraud\monitoring\2025-12-05\drift_summary.csv)

- [metrics.json](fraud_detection_system\sample_outputs\fraud\monitoring\2025-12-05\metrics.json)

- [fraud_daily_report.html](fraud_detection_system\sample_outputs\fraud\reports\2025-12-05\fraud_daily_report.html)

- [kpis.json](fraud_detection_system\sample_outputs\fraud\reports\2025-12-05\kpis.json)
---

## 4. Architecture at a glance

High-level layout:

```text
credit_scoring_system/
  data/featurestore/
  models/
  reports/          # daily + monthly reports (Stage 6)
  scripts/          # training + scoring
  docs/model_cards/ # credit_model.md

fraud_detection_system/
  data/features_batch/, features_stream/
  models/           # CAND_YYYYMMDD, PROD_POINTER.txt
  api/              # FastAPI /score (8001)
  rules/rules_v1.yml
  docs/model_cards/ # fraud_model.md

shared_env/
  orchestration/flows/  # credit_daily_flow.py, fraud_daily_flow.py,
                        # monthly_credit_rollup_flow.py
  monitoring/           # monitor_credit_drift.py, monitor_fraud_api_logs.py,
                        # alert_bridge.py
  ci/                   # governance_gate.py
  backup/               # nightly_snapshot.py (DVC + zipped reports)
  ops/                  # tasks_export.ps1, tasks_import.ps1
  contracts/            # validate_credit_outputs.py, validate_fraud_logs.py

docs/
  ARCHITECTURE.md
  CREDIT_OVERVIEW.md
  FRAUD_OVERVIEW.md
  OPS_AND_GOVERNANCE.md
  model_cards/          # public copies of credit/fraud model cards

docs_global/            # local-only monitoring, reports, audit packs, runbooks
docs_site/              # static showroom (Cloudflare)
data/                   # raw + kaggle (gitignored)
mlruns/                 # MLflow experiments (gitignored)
```

Details:

- **MLflow:** local tracking at `mlruns/` (see MLflow UI on port 5000)
- **DVC:** snapshots of key data & reports; `nightly_snapshot.py` runs `dvc push`
- **Governance:** model cards, rules changelog, audit packs, CI gate

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for a deeper breakdown.

---

## 5. Repo layout (top-level)

- `credit_scoring_system/` — all credit features, models, scoring scripts, reports
- `fraud_detection_system/` — fraud features, models, API, rules, analysis
- `shared_env/` — orchestration, monitoring, CI, backup, contracts
- `docs_site/` — static site for Cloudflare + local demo
- `docs/` — public documentation and model cards
- `docs_global/` — local monitoring/reports/audit packs/runbooks (gitignored)
- `data/` — `kaggle/` (credit + fraud raw; gitignored), `raw/` for other sources
- `scripts/` — helper scripts, incl. `build_demo_data_from_kaggle.py`
- `.github/` — CI workflows (`reporting-smoke`, `data-contract-smoke`, `fraud-api-smoke`, etc.)
- `requirements.txt`, `requirements.lock` — dependencies (dev vs frozen)

---

## 6. How to run things (pointer)

For detailed run instructions:

- **Tasks & flows:** see [TASKS_GUIDE.md](TASKS_GUIDE.md)
- **Local live API demo:** see [LOCAL_DEMO_GUIDE.md](LOCAL_DEMO_GUIDE.md)
- **System design:** see [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Credit details:** see [CREDIT_OVERVIEW.md](docs/CREDIT_OVERVIEW.md)
- **Fraud details:** see [FRAUD_OVERVIEW.md](docs/FRAUD_OVERVIEW.md)
- **Governance & CI:** see [OPS_AND_GOVERNANCE.md](docs/OPS_AND_GOVERNANCE.md)

---

## 7. Tech stack (short version) 

- **Languages / Core:** Python 3.13, SQL-ish style via pandas
- **Models:** scikit-learn, XGBoost
- **APIs:** FastAPI + Uvicorn (fraud + credit), FastAPI gateway
- **Tracking:** MLflow (local file backend)
- **Data versioning:** DVC (local remote `_dvc_remote`)
- **Monitoring:** Evidently, custom validators, JSON/CSV/HTML reports
- **Orchestration:** Simple Python “flows” + Windows Task Scheduler
- **Frontend:** Static HTML/CSS/JS showroom (docs_site) on Cloudflare Pages
- **BI:** Tableau seed [Risk_Analytics_seed.twbx](docs_global\bi\tableau\Risk_Analytics_seed.twbx) 

---

## 8. How to evaluate this as a hiring manager

If you’re reviewing this repo:

1. **Scan the README + ARCHITECTURE** to see the full system shape.
2. **Open docs_site** (hosted URL) to see the user-facing side.
3. **Glance at MLflow + docs_global** (locally) to see real monitoring outputs.
4. **Skim the model cards + audit pack** to see governance and release discipline.
5. Optionally:
   - Run `credit_daily_flow.py` and `fraud_daily_flow.py`
   - Run `shared_env\ci\governance_gate.py` to see CI logic locally
   - Trigger the alert bridge test once

The repo is meant to look and behave like a realistic, self-contained **risk analytics platform**, not just notebook.
