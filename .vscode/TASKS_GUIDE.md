# VS Code Tasks — Guide & Index (Stage 7, Revised)

**Root:** `C:\DevProjects\risk_analysis_flagship`  
**Interpreter:** `.venv\Scripts\python.exe`  
**MLflow store:** `file:///C:/DevProjects/risk_analysis_flagship/mlruns`

> This replaces the older “Daily Starter Pack” based on the legacy *Daily: CREDIT full chain* and aligns with your new **Orch** flows. (Old structure for reference: Daily Starter Pack in previous guide lines 9–15. :contentReference[oaicite:0]{index=0})

---

## 🔰 Daily Task + Success Criteria (run in this order)

### A) Kick off
1) **Orch: Credit Daily Flow (Stage 5→4→6)**  
   End-to-end for credit (monitor→score→daily report).  
   *Success:*  
   - `docs_global\monitoring\credit\YYYY-MM-DD\` folder created for today  
   - `credit_scoring_system\outputs\scoring\pd_scores_YYYYMMDD.parquet` exists  
   - `docs_global\reports\credit\YYYY-MM-DD\credit_daily_report.html` exists  
   - MLflow shows today’s runs for monitoring, scoring, and daily report

2) **Orch: Fraud Daily Flow (Stage 5→7)**  
   Runs fraud monitoring + (when implemented) daily fraud report.  
   *Success:*  
   - `docs_global\monitoring\fraud\YYYY-MM-DD\` folder created for today  
   - (If report exists) `docs_global\reports\fraud\YYYY-MM-DD\fraud_daily_report.html` exists  
   - MLflow shows today’s fraud monitoring (and report, when available)

3) **Open: Today’s Credit Daily Report**  
   Opens today’s HTML to visually confirm KPIs and charts render cleanly.

4) **MLflow: UI (project mlruns)**  
   Open MLflow at port **5000** and confirm runs landed in the right experiments.

> References to these tasks in your current `tasks.json`:  
> Orch: Credit Daily Flow (lines show label/command). :contentReference[oaicite:1]{index=1}  
> Orch: Fraud Daily Flow (lines show label/command). :contentReference[oaicite:2]{index=2}  
> MLflow: UI (port, backend store). :contentReference[oaicite:3]{index=3}

5) **Fraud: Stage 7 — Daily Report (Today)**
  Success:
> docs_global\reports\fraud\YYYY-MM-DD\kpis.json exists
> docs_global\reports\fraud\YYYY-MM-DD\fraud_daily_report.html opens cleanly
> MLflow experiment fraud_stage7_daily_reporting has today’s run with metrics + artifacts
> If A/B is active: table shows arm=prod|cand with per-arm flagged%

---

### B) If anything fails (surgical reruns)
- **Monitoring: Credit (daily)** → re-run Stage-5 credit monitor  
- **Credit: Stage 4 — Batch Scoring** → re-build today’s PD/rollups  
- **Credit: Daily Report (Stage 6)** → re-render today’s HTML  
- **Monitoring: Fraud (daily)** → re-run fraud monitor  
- **Open: Latest Credit Daily Report** → view newest daily HTML (today or latest)

*(Older guide sections for single steps and utilities are still relevant, now reorganized under the new Orch flows. Previous single-step descriptions: lines 28–35. :contentReference[oaicite:4]{index=4})*

---

## 🗓 End-of-Month / On-Demand

- **Orch: Monthly Credit Roll-up**  
  Writes: `docs_global\reports\credit\YYYY-MM\credit_monthly_summary.html`  
- **Open: This Month's Credit Summary**  
  Opens the month’s summary HTML for a quick check.

*(Older wording about EOM outputs for context: lines 19–24. :contentReference[oaicite:5]{index=5})*

---

## ⚙️ Services & Utilities

- **Fraud API (reload)** → Dev server for real-time scoring during manual tests. :contentReference[oaicite:6]{index=6}  
- **Servers: Discover & Build Index / Update Index Status / Start All / Stop All / Status** → Local services helpers (index, lifecycle). :contentReference[oaicite:7]{index=7}  
- **DVC: repro** → Rebuild DVC pipeline (when you change data or stages). :contentReference[oaicite:8]{index=8}  
- **Python: run script (prompt)** → Ad-hoc runner for one-off scripts.

---

## 📋 Daily Pre-Build Checklist (copy/pin this in your notes)

- [ ] Ran **Orch: Credit Daily Flow** successfully (see “Success” bullets above)  
- [ ] Ran **Orch: Fraud Daily Flow** successfully  
- [ ] Opened **Today’s Credit Daily Report** and verified:
      - KPIs render; no missing charts or “N/A” sections  
      - Date/time stamp matches today; sample size > 0  
- [ ] MLflow UI shows **today’s** runs:
      - Credit monitoring, scoring, daily reporting  
      - Fraud monitoring (and report when implemented)  
- [ ] Disk snapshots in expected folders for **today** (credit & fraud monitoring, credit report)  
- [ ] If any red flags/drift alerts appear → create a quick note and re-run the precise single-step task (monitor/score/report) before coding

---

## 🧪 Troubleshooting Q&A (quick)

**Q1: Flow failed with a path error**  
Check that you’re running from the repo root and the *Orch* tasks have `cwd` set to `${workspaceFolder}` (as in your tasks). :contentReference[oaicite:9]{index=9}

**Q2: MLflow shows nothing for today**  
Launch **MLflow: UI (project mlruns)** and confirm it points to your repo `mlruns` store (port 5000, backend store URI). :contentReference[oaicite:10]{index=10}

**Q3: HTML opened but sections look empty**  
Re-run **Credit: Stage 4 — Batch Scoring** then **Credit: Daily Report (Stage 6)** to regenerate KPIs from the latest scores.

---

## 🔎 Notes / Conventions (unchanged)

- All tasks assume the venv at `.venv\Scripts\python.exe`. :contentReference[oaicite:11]{index=11}  
- Daily credit HTML path pattern:  
  `docs_global\reports\credit\YYYY-MM-DD\credit_daily_report.html` :contentReference[oaicite:12]{index=12}

---

## 🧾 Change Log

- **2025-10-16**  
  - Replaced legacy “Daily full chain” with **Orch: Credit Daily Flow** and added **Orch: Fraud Daily Flow** as the morning entry points.  
  - Introduced **Daily Task + Success Criteria** section to gate daily build work.  
  - Consolidated single-step tasks under “If anything fails (surgical reruns)”.

- **2025-10-13 ~ 2025-10-10 (legacy guide for context)**  
  Earlier guide listed the legacy daily chain and single-steps (now superseded by Orch flows). :contentReference[oaicite:13]{index=13} :contentReference[oaicite:14]{index=14}
