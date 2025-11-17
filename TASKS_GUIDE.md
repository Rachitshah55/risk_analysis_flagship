# TASKS_GUIDE — How to Run Flows, APIs, and Demos

This guide tells you **which tasks to run** and **what they do**.  
Assumes Windows + Python 3.13 and this repo at:

- `C:\DevProjects\risk_analysis_flagship`

---

## 1. Prerequisites

### 1.1. Environment

From PowerShell:

```bash
cd C:\DevProjects\risk_analysis_flagship

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
# or: pip install -r requirements.lock
```

### 1.2. Common services (optional but useful)

- **MLflow UI:**  
  Run once in a dedicated terminal:

  ```bash
  mlflow ui --backend-store-uri mlruns --port 5000
  ```

  Visit `http://127.0.0.1:5000`.

---

## 2. Orchestrated daily flows (canonical entry points)

These are the **main daily chains** used by the project.

### 2.1. Credit — Daily Flow (Stage 5 → 4 → 6)

**Via Void IDE (recommended):**

- `Run Task…` → **Orch: Credit Daily Flow (Stage 5→4→6)**

**Via CLI:**

From repo root with venv active:

```bash
python shared_env\orchestration\flows\credit_daily_flow.py
```

This will:

- Run credit drift monitor (Stage 5)
- Run credit portfolio scoring (Stage 4)
- Render daily HTML report (Stage 6)
- Export BI-friendly CSVs for Tableau

**Key outputs (today’s date):**

- `credit_scoring_system\outputs\scoring\pd_scores_YYYYMMDD.parquet`
- `docs_global\monitoring\credit\YYYY-MM-DD\drift_report.html`
- `docs_global\reports\credit\YYYY-MM-DD\credit_daily_report.html`

---

### 2.2. Fraud — Daily Flow (Stage 5 → 7)

**Via Void IDE:**

- `Run Task…` → **Orch: Fraud Daily Flow (Stage 5→7)**

**Via CLI:**

```bash
python shared_env\orchestration\flows\fraud_daily_flow.py
```

This will:

- Parse fraud API logs for the day
- Compute latency and detection KPIs
- Generate drift report for key features
- Export BI CSVs

**Key outputs (today’s date):**

- `docs_global\monitoring\fraud\YYYY-MM-DD\summary.csv`
- `docs_global\monitoring\fraud\YYYY-MM-DD\summary.json`
- `docs_global\monitoring\fraud\YYYY-MM-DD\raw_current.csv`
- `docs_global\monitoring\fraud\YYYY-MM-DD\drift_report.html`

---

## 3. Monthly roll-ups

### 3.1. Credit — Monthly Roll-up

**Via Void IDE:**

- `Run Task…` → **Orch: Monthly Credit Roll-up**

**Via CLI (auto current month):**

```bash
python shared_env\orchestration\flows\monthly_credit_rollup_flow.py
```

This wraps:

- `credit_scoring_system\reports\rollup_month_credit_reports.py`

**Output:**

- `docs_global\reports\credit\YYYY-MM\credit_monthly_summary.html`

---

### 3.2. Fraud — Monthly Summary

Monthly fraud roll-up is more manual:

**Via Void IDE:**

- `Run Task…` → **Fraud: Stage 7 — Monthly Roll-up (auto YYYY-MM)**
- `Run Task…` → **Open: This Month's Fraud Summary**

**Via CLI (example month):**

```bash
python fraud_detection_system\reports\rollup_month_fraud_reports.py --month 2025-09
```

**Outputs:**

- `docs_global\reports\fraud\YYYY-MM\fraud_monthly_summary.html`
- `docs_global\reports\fraud\YYYY-MM\monthly_kpis.json`

---

## 4. Monitoring only (no scoring)

If you just want to run monitors.

### 4.1. Credit drift & calibration

```bash
python shared_env\monitoring\monitor_credit_drift.py
```

- Looks at the two most recent:
  - `credit_scoring_system\outputs\scoring\pd_scores_YYYYMMDD.parquet`
- Writes:
  - `docs_global\monitoring\credit\YYYY-MM\drift_report.html`
  - `docs_global\monitoring\credit\YYYY-MM\drift_summary.csv`
  - `docs_global\monitoring\credit\YYYY-MM\alert.txt` (if PSI ≥ 0.25)

### 4.2. Fraud API logs

```bash
python shared_env\monitoring\monitor_fraud_api_logs.py
```

- Reads:
  - `fraud_detection_system\api\logs\YYYYMMDD.jsonl`
  - optional shadow logs: `YYYYMMDD_shadow.jsonl`
- Writes (per day):
  - `docs_global\monitoring\fraud\YYYY-MM-DD\summary.csv`
  - `docs_global\monitoring\fraud\YYYY-MM-DD\summary.json`
  - `docs_global\monitoring\fraud\YYYY-MM-DD\raw_current.csv`
  - `docs_global\monitoring\fraud\YYYY-MM-DD\drift_report.html`

---

## 5. APIs & gateway

### 5.1. Fraud Scoring API (port 8001)

**CLI:**

```bash
python fraud_detection_system\api\run_api.py
```

- Endpoints:
  - `GET /health`
  - `POST /score` (JSON transaction → fraud score + flags)
- Logs:
  - `fraud_detection_system\api\logs\YYYYMMDD.jsonl`
  - `fraud_detection_system\api\logs\YYYYMMDD_shadow.jsonl` (shadow model)

### 5.2. Credit Scoring API (port 8002)

The credit API is exposed via a VS Code / Void IDE task:

- `Run Task…` → **Credit API (dev)**

Under the hood this runs a Uvicorn command to serve the credit FastAPI app on port **8002**.

If you prefer pure CLI:

- Open `.vscode\tasks.json`
- Inspect the command for the **Credit API** task
- Run that exact command from the terminal

Once running:

- `GET http://127.0.0.1:8002/health` → should show active credit model path
- `POST http://127.0.0.1:8002/score` → JSON payload → PD/EL output

### 5.3. API Gateway for docs_site (port 8000)

Used in **local demo mode** to route docs_site calls.

**CLI:**

```bash
python -m uvicorn shared_env.api_gateway:app --port 8000
```

Gateway behavior:

- Proxies credit requests to `http://127.0.0.1:8002/score`
- Proxies fraud requests to `http://127.0.0.1:8001/score`
- Injects `account_age_days` into fraud payload when missing (for schema compatibility)
- CORS configured for `http://127.0.0.1:8010`

---

## 6. docs_site showroom

### 6.1. Serve static site locally

From repo root:

```bash
python -m http.server 8010
```

Then open:

- `http://127.0.0.1:8010/docs_site/`

See `LOCAL_DEMO_GUIDE.md` for **how to flip config.json** between hosted vs local mode and how to run APIs + gateway.

---

## 7. Alert bridge

Alert bridge sends Slack + Gmail/SMTP notifications once `.env` is configured.

**CLI:**

```bash
python shared_env\monitoring\alert_bridge.py --test --severity warn
```

Variants:

- `--slack-only` — Slack only
- `--email-only` — email only
- `--print-config` — debug current settings

Wiring of Slack/Gmail is described in `docs/OPS_AND_GOVERNANCE.md`.

---

## 8. Governance tools (local)

### 8.1. Governance gate

Run local CI governance gate:

```bash
python shared_env\ci\governance_gate.py
```

This checks:

- Whether model cards were updated for PROD swaps
- Whether rules changelog was updated for rules changes
- Basic hygiene on audit pack evidence

### 8.2. Audit pack builder

Build a dated audit pack:

```bash
python shared_env\ops\build_audit_pack.py
```

Outputs to:

- `docs_global\audits\YYYY-MM-DD\`

Contents include:

- Model cards
- Rules file + changelog
- PROD pointer snapshots
- Key monitoring/report artifacts

Details in `docs/OPS_AND_GOVERNANCE.md`.

---

## 9. Windows Task Scheduler (steady state)

Three main scheduled tasks (Stage 8–9):

- **Credit Daily** → `credit_daily_flow.py`
- **Fraud Detect Daily** → `fraud_daily_flow.py`
- **Credit EOM Roll-up** → `monthly_credit_rollup_flow.py`

Exports live in:

- `docs_global\runbooks\scheduler_exports\`
  - `Credit Daily.xml`
  - `Fraud Detect Daily.xml`
  - `Credit EOM Roll-up.xml`

To re-import on a new machine:

- Use Task Scheduler GUI → Import Task… → select the XML
- Ensure it uses the project `.venv` and repo path
- See `docs/OPS_AND_GOVERNANCE.md` for recommended schedule times
