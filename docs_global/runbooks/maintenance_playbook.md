# Maintenance & Change-Control Playbook (Stage 9 Steady State)

This document defines how to operate, update, and safely evolve the system without breakage.

## 0) Roles & Approvals
- **Owner**: day-to-day ops, minor fixes, prepares changes.
- **Risk Lead**: approves rules/model changes and thresholds.
- **Release Manager**: merges release PRs, tags releases.

## 1) Cadence & Routine
### Daily (automatic, Task Scheduler)
- Credit: run daily flow; publish `docs_global/reports/credit/YYYY-MM-DD/*` and `bi/credit/*`.
- Fraud: run daily flow; publish `docs_global/reports/fraud/YYYY-MM-DD/*` and `bi/fraud/*`.
- Monitoring: write to `docs_global/monitoring/{credit|fraud}/YYYY-MM-DD/`.
- Alerts: Gmail bridge sends when PSI/latency thresholds exceeded.

### Weekly (manual 10–15 min)
- Review alert emails and monitoring folders for anomalies.
- Spot-check API latency via `/health` and `/score` (1–2 vectors).
- Ensure Task Scheduler last‐run times look sane.

### Monthly (EOM)
- Run “Gov: Build Audit Pack (Today)” on the last day → commit the new dated folder.
- If needed, publish a release PR `release/YYYY-MM-DD`.

## 2) Change Types & Required Artifacts

### A. Rules-only change (Fraud)
- **Branch**: `feat/rules-v1.0.1`  
- **Update**: edit `fraud_detection_system/rules/rules_*.yml`.  
- **Also update (required)**:
  - `fraud_detection_system/rules/CHANGELOG.md` → add `## v1.0.1 - YYYY-MM-DD`, rationale, sign-offs.
- **Tests**:
  - Local: run API; `/health` and 1–2 `/score` vectors.
  - CI: governance-gate enforces changelog bump.
- **Docs**: none required beyond changelog.
- **Deploy**: merge PR; (optional) build audit pack if releasing.

### B. Model retrain (Credit or Fraud)
- **Branch**: `feat/model-<credit|fraud>-YYYYMMDD`.
- **Update**: new artifact produced, pointer change when promoting.
- **Also update (required)**:
  - Model card: `docs/model_cards/<credit|fraud>_model.md`  
    - “Change Log” section: reason, data window, metrics (AUC/PR-AUC/KS), MLflow run ID(s).
- **Tests**:
  - Local/offline: metrics better or justified (tradeoff documented).
  - API (for Fraud): `/health` OK; `/score` returns expected schema.
- **Docs**: consider adding a short A/B comparison note to the audit pack.
- **Deploy**: update `PROD_POINTER.txt` to new artifact path in same PR.

### C. PROD pointer swap (Hotfix)
- **Branch**: `hotfix/fraud-pointer-YYYYMMDD` (or credit).  
- **Update**: `PROD_POINTER.txt` only.  
- **Also update (required)**:
  - Model card “Change Log” (pointer-only note + smoke evidence).
- **Tests**:
  - API `/health` and `/score`.  
- **Deploy**: merge; optionally draft a short rollback note in audit pack.

### D. Monitoring threshold change
- **Branch**: `chore/thresholds-YYYYMMDD`.  
- **Update**: `shared_env/monitoring/alert_thresholds.yml`.  
- **Also update (recommended)**:
  - Add a one-liner in relevant model card “Change Log” (context for future auditors).
- **Tests**: run a simulated breach locally to confirm alert bridge.

### E. API behavior change (schemas, fields)
- **Branch**: `feat/api-change-<short>`.  
- **Update**: code + OpenAPI.  
- **Also update (required)**:
  - Data-contract tests (CI `data-contract-smoke`) to new schema.
  - README: document request/response example.  
- **Tests**: update integration tests; run governance-gate (should pass).

## 3) Safe Workflow (applies to any change)
1. **Create a branch** with descriptive name.  
2. **Run local checks**:  
   - `.venv\Scripts\python.exe shared_env\ci\governance_gate.py`  
   - Start Fraud API locally; hit `/health`, then `/score`.  
   - Run a daily flow dry-run if your change touches reporting.  
3. **Update artifacts** per change type (changelog, model card, pointer).  
4. **Build an audit pack** (if the change will be released):  
   - Run “Gov: Build Audit Pack (Today)” → commit the new folder.  
5. **Open PR** — template checklist must be green.  
6. **CI passes** → reviewer approval → merge.  
7. **Release**: tag or release branch if needed.

## 4) Versioning & Naming
- **Rules**: SemVer in `CHANGELOG.md` (v1.0.1 etc.).  
- **Models**: artifact names include date/time, e.g., `models/fraud_xgb_20251029.pkl`.  
- **Branches**: `feat/…`, `chore/…`, `hotfix/…`, `release/YYYY-MM-DD`.  
- **Tags**: `vMAJOR.MINOR.PATCH` tied to a dated audit pack.

## 5) Backout / Rollback
- Use the “Rollback Fraud PROD” runbook.  
- For credit, replace the pointer (or config) to prior artifact; rebuild audit pack with a rollback note.  
- Always add a short RCA line to the next audit pack.

## 6) Secrets & Config
- Secrets live **only** in `shared_env/secrets/` (ignored by Git).  
- Rotate if ever pushed; the Gmail token re-auths automatically when missing.  
- Keep `.env.template` updated; never commit `.env`.

## 7) Health & Monitoring SLOs (suggested)
- Fraud API: p95 latency < 300 ms (local runner), error rate < 1%.  
- Credit monitoring: PSI warn ≥ 0.2, error ≥ 0.25 (tune per history).  
- Alert routing: email only for `warn` and higher (to reduce noise).

## 8) Ops Hub (folder of truth)
- `docs_global/runbooks/` — all SOPs and exports.  
- `docs_global/audits/` — dated evidence folders.  
- `docs/model_cards/` — living model documentation.  
- `.github/` — PR template + CI gates.  
- `docs_global/config/PROJECT_FACTS_LOCK.md` — fast facts (Credit=daily primary).


## Tableau
Tableau seed workbook (.twbx)

Goal: a tiny dashboard you can show/install anywhere. Save to:
docs_global\bi\tableau\Risk_Analytics_seed.twbx

Create (Tableau Public/Desktop):

1 Open Tableau → Connect → Text file → pick docs_global\bi\credit\kpis_daily.csv.

2 Verify fields:

Parse date as Date.

Ensure numeric KPI columns (e.g., pd_avg, ks, etc.) are Numbers.

3 Sheet “Credit KPI Trend”:

Drag date to Columns, pd_avg to Rows (or your key KPI).

Add ks as a secondary axis or a separate sheet if you prefer cleaner visuals.

4 Add second data source:

Text file → docs_global\bi\fraud\metrics_daily.csv.

5 Sheet “Fraud Metrics”:

date to Columns, precision_at_k (or your main metric) to Rows; add recall_at_k as tooltip or second view.

6 Dashboard:

Title: “Risk Analytics Seed”.

Place both sheets. Keep it minimal and readable.

7 File → Save As → choose Tableau Packaged Workbook (.twbx) →
docs_global\bi\tableau\Risk_Analytics_seed.twbx.

(Optional) Preview PNGs for README:

Export each sheet as PNG and save under docs_global\bi\tableau\_previews\.