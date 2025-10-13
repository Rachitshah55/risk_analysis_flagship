# VS Code Tasks — Guide & Index

**Root:** `C:\DevProjects\risk_analysis_flagship`  
**Interpreter:** `.venv\Scripts\python.exe`  
**MLflow store:** `file:///C:/DevProjects/risk_analysis_flagship/mlruns`

---

## 🔰 Daily Starter Pack (run in this order)
1. **Daily: CREDIT full chain (S5 → S4 → S6)**  
   Runs Stage 5 monitor → Stage 4 batch scoring → Stage 6 daily report (HTML) and logs MLflow.
2. **Open: Today’s Credit Daily Report**  ← *opens today’s HTML in your browser*  
3. **MLflow: UI (project mlruns)**  ← *opens UI on the same local store the runs write to*

> Tip: if you’re reviewing yesterday/today, use **Open: Latest Credit Daily Report**.

---

## 🗓 EOM / On-Demand
- **Credit: Stage 6 — Monthly Roll-up (auto YYYY-MM)**  
  Aggregates daily reports → writes `docs_global\reports\credit\YYYY-MM\credit_monthly_summary.html`
  and logs MLflow (`credit_stage6_monthly_rollup`).
- **Open: This Month's Credit Summary**  
  Opens the monthly summary HTML for the current month.

---

## ⚙️ Individual Steps / Utilities
- **Shared: Run Stage 5 Credit Monitor (Today)** — Produces `docs_global\monitoring\credit\YYYY-MM-DD\…` (required for Stage 6).
- **Credit: Stage 4 — Batch Scoring** — Produces:
  - `credit_scoring_system\outputs\scoring\pd_scores_YYYYMMDD.parquet` (must contain `pd`)
  - `credit_scoring_system\outputs\scoring\segment_rollups_YYYYMMDD.parquet` (must contain `EL` / `expected_loss`)
- **Credit: Stage 6 — Daily Report (Today)** — Renders the notebook and logs `credit_stage6_daily_reporting`.
- **Open: Latest Credit Daily Report**  ← *opens newest daily HTML without thinking about the date*
- **MLflow: UI (project mlruns)** — MLflow UI pinned to the repo’s `mlruns` store.

**Other helpers** (leave as-is unless you need them)
- **Fraud API (reload)** — dev server on port 8001.
- **Servers: Start/Stop/Status** — local services helpers.
- **DVC: repro** — rebuild DVC pipeline.
- **Prefect: run flow.py** — dev-only flow runner.

---

## 🔎 Notes / Conventions
- All tasks assume the venv at `.venv\Scripts\python.exe`.
- MLflow UI should always use the repo’s `mlruns` store so runs appear immediately.
- Stage 6 relies on Stage 5 outputs for **today**; Stage 4 fills PD/EL KPIs (optional but recommended).
- Daily report HTML path pattern:
  `docs_global\reports\credit\YYYY-MM-DD\credit_daily_report.html`

---

## 🧾 Change Log (who/when/why)
- **2025-10-13**
  - Added **Open: Today’s Credit Daily Report** (Python helper, no PowerShell quoting issues).
  - Added **Open: Latest Credit Daily Report** (opens newest day automatically).
- **2025-10-12**
  - Fixed **Daily full chain** to detect `score_credit_portfolio.py` for Stage 4.
  - Hardened EL parsing in Stage 6 to accept `EL`, `expected_loss`, `el_total`, and string values with commas.
  - Pinned **MLflow: UI (project mlruns)** task to the venv Python and explicit backend store.
- **2025-10-10**
  - Added Stage 6 daily report + monthly roll-up tasks.
  - Initial Daily Starter Pack and Stage 5 monitor task.
