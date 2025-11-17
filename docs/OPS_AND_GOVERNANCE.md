# OPS_AND_GOVERNANCE — CI, Scheduler, Audit Packs, and Alerts

This document explains **how operations are controlled and audited**: CI checks, governance gates, scheduler setup, backups, and alerting.

---

## 1. Project facts and configuration

Authoritative project facts are stored in:

- `docs_global\config\PROJECT_FACTS_LOCK.md`

Key points:

- **Credit:**
  - Reporting primary = **daily**
  - Monthly roll-up = derived at EOM
- **Fraud:**
  - Stage 6 = retrain + shadow A/B + MLflow promotion
  - Stage 7 = daily ops reporting

This file is the “ground truth” for what the system is supposed to do at steady state.

---

## 2. CI workflows

Location:

- `.github\workflows\ci.yml`

Main jobs:

1. **reporting-smoke**
   - Runs key reporting flows (e.g. daily and/or monthly) on a small subset
   - Verifies that HTML reports and KPIs are generated
2. **unit-min**
   - Minimal unit tests on critical modules
   - Sanity check for Python 3.13 env / imports
3. **data-contract-smoke**
   - Runs validators:
     - `shared_env\contracts\validate_credit_outputs.py`
     - `shared_env\contracts\validate_fraud_logs.py`
   - Ensures outputs have expected schema/file shapes
4. **api-http-integration**
   - Spins up API (without reload)
   - Probes `/health` and/or `/score`
   - Uses strict dependencies and no background runaway processes
5. **fraud-api-smoke**
   - Specialized readiness probe for fraud API
   - Uses `/health` polling with correct Uvicorn options (`--lifespan on`, no `--reload`)

Branch protection can be configured to **require**:

- `reporting-smoke`
- `data-contract-smoke`
- `fraud-api-smoke`
- (optionally) others once stable

---

## 3. Governance gate

Script:

- `shared_env\ci\governance_gate.py`

Purpose:

- Run **locally** or as part of CI to enforce governance discipline.

Checks include:

- When `fraud_detection_system\models\PROD_POINTER.txt` changes:
  - `docs\model_cards\fraud_model.md` must be updated with a corresponding entry
  - `fraud_detection_system\rules\CHANGELOG.md` must be updated if rules changed
- When credit model is updated:
  - `docs\model_cards\credit_model.md` must be updated
- Audit pack presence:
  - A dated directory under `docs_global\audits\YYYY-MM-DD\` must exist for releases
  - Model cards, rules file, PROD pointer, and evidence must be present

Typical output (on success):

- `[OK] Governance checks passed.`

This gate is wired into CI as a job and can also be run manually before merges.

---

## 4. Audit packs

Script:

- `shared_env\ops\build_audit_pack.py`

Usage:

```bash
python shared_env\ops\build_audit_pack.py
```

Outputs:

- `docs_global\audits\YYYY-MM-DD\`
  - `credit\credit_model.md`
  - `fraud\fraud_model.md`
  - Copies of:
    - `fraud_detection_system\rules\rules_v1.yml`
    - `fraud_detection_system\rules\CHANGELOG.md`
    - `fraud_detection_system\models\PROD_POINTER.txt`
  - Evidence JSON:
    - Metrics and links to monitoring/report files
  - `APPROVALS_TEMPLATE.md`:
    - Space for sign-off notes (managers, risk, compliance)
  - `evidence.json`:
    - Machine-readable summary used by governance gate

Purpose:

- Provide a **snapshot** for regulators / internal audit:
  - What model is live
  - What rules are live
  - What monitoring reports existed at the time
  - Who approved the change

---

## 5. Runbooks

Location:

- `docs_global\runbooks\`

Key runbooks:

- `incident_drift_credit.md`
  - Steps to investigate high drift in credit PD/EL
- `incident_latency_fraud.md`
  - Steps to investigate fraud API latency spikes
- `fraud_ab_promotion.md`
  - Human-centered A/B evaluation procedure
- `rollback_fraud_prod.md`
  - How to revert PROD pointer to a previous candidate
- `scheduler_exports\`
  - `Credit Daily.xml`
  - `Fraud Detect Daily.xml`
  - `Credit EOM Roll-up.xml`

These documents describe **what to do when something goes wrong**, not just how to run the happy path.

---

## 6. Scheduler and steady-state operations

### 6.1. Tasks & exports

Windows Task Scheduler tasks (Stage 8–9):

- **Credit Daily**
  - Calls `credit_daily_flow.py` at 08:00
- **Fraud Detect Daily**
  - Calls `fraud_daily_flow.py` at 08:05
- **Credit EOM Roll-up**
  - Calls `monthly_credit_rollup_flow.py` on the last day at 23:00

Exports:

- `docs_global\runbooks\scheduler_exports\Credit Daily.xml`
- `docs_global\runbooks\scheduler_exports\Fraud Detect Daily.xml`
- `docs_global\runbooks\scheduler_exports\Credit EOM Roll-up.xml`

### 6.2. Importing tasks on a new machine

Steps:

1. Open **Task Scheduler**
2. `Import Task…`
3. Choose the appropriate XML from `scheduler_exports`
4. Edit the task:
   - Ensure the **action** points to:
     - `C:\DevProjects\risk_analysis_flagship\.venv\Scripts\python.exe`
   - Set “Start in” to:
     - `C:\DevProjects\risk_analysis_flagship`
   - Script argument:
     - `shared_env\orchestration\flows\credit_daily_flow.py` or equivalent
5. Run each task manually once to confirm success

---

## 7. Backups and DVC

Script:

- `shared_env\backup\nightly_snapshot.py`

Responsibilities:

- `dvc push` for tracked data and artifacts
- Zip selected `docs_global\reports\**` directories
- Optionally log runtime and success status

Intended schedule:

- Nightly run (e.g. 23:30) via Task Scheduler

This ensures:

- Data + reports for any given day/month can be re-produced or restored
- DVC remote `_dvc_remote\` stays up to date

---

## 8. Alerting and `.env` configuration

Alert bridge:

- `shared_env\monitoring\alert_bridge.py`

Supports:

- Slack (Incoming Webhook)
- Gmail API and/or SMTP
- Severity filtering via `ALERT_MIN_SEVERITY`

### 8.1. .env template

`.env.template` (kept in repo) defines variables like:

- `ALERT_MIN_SEVERITY`
- `SLACK_WEBHOOK_URL`
- `EMAIL_TRANSPORT` (`gmail_api` or `smtp`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- Gmail OAuth file / token locations if using Gmail API

Copy to `.env` (gitignored) and fill in secrets.

### 8.2. Testing alert bridge

Run:

```bash
python shared_env\monitoring\alert_bridge.py --test --severity warn
```

Variants:

- `--slack-only` → Slack ping
- `--email-only` → email ping

Once configured, flows can call the bridge at the end of daily chains or on critical conditions (e.g. high drift, missing KPIs, API latency spikes).

---

## 9. Tableau / BI integration

Location:

- `docs_global\bi\tableau\`

Key files:

- `Risk_Analytics_seed.twbx` — Tableau workbook
- `README.md` — explains how to wire it to local CSVs

Daily BI sources (live pipelines):

- `docs_global\bi\credit\...` (populated by flows)
- `docs_global\bi\fraud\...`

Hosted demo BI sources (static):

- `docs_site\demo_data\credit\kpis_daily.csv`
- `docs_site\demo_data\fraud\kpis_daily.csv`
- `docs_site\demo_data\fraud\metrics_daily.csv`

This allows:

- Local Tableau dashboards bound to live outputs
- Hosted site charts bound to static CSVs for recruiters

---

## 10. Version freeze and environment

Files:

- `requirements.txt` — main dev dependencies
- `requirements.lock` — frozen versions from working venv

`requirements.lock` generated via:

```bash
.\.venv\Scripts\python.exe -m pip freeze > requirements.lock
```

CI installs from `requirements.lock` to guarantee reproducible environments.

---

## 11. Steady-state change process

When making changes in production-like flow:

1. **Model change (credit or fraud)**
   - Train candidate
   - Generate evaluation / A/B reports
   - Update model card
   - Update PROD pointer
2. **Rules change (fraud)**
   - Update `rules_v1.yml`
   - Update `rules\CHANGELOG.md`
3. **Audit pack**
   - Run `build_audit_pack.py`
4. **Governance gate**
   - Run `governance_gate.py`
5. **Tag & release**
   - Create GitHub release (e.g. `v1.0.0`)
   - Note relevant `docs_global\audits\YYYY-MM-DD\` path

This gives you a compact, repeatable process that looks like a small but disciplined risk team’s operating model.
