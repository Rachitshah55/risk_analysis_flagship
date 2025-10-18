# docs_global/bi/TABLEAU_TODO.md

## Purpose
Defer full Tableau build until pipelines are done. This checklist captures exactly what to do later to connect Tableau to the project with minimal rework.

---

## 0) When to do this
- After Stage 7 is fully stable and daily exports are flowing.
- Confirm these files exist for a few consecutive days:
  - `docs_global/bi/credit/kpis_daily.csv`
  - `docs_global/bi/credit/segment_rollups_YYYYMMDD.csv` (daily files; wildcard union)
  - `docs_global/bi/fraud/kpis_daily.csv`
  - `docs_global/bi/fraud/metrics_daily.csv`
  - Optional drift detail when present: `docs_global/bi/fraud/raw/YYYY-MM-DD/drift_summary.csv`

---

## 1) Prereqs
- Install **Tableau Public (free)** or **Tableau Desktop**.
- Ensure Windows account has read/write access to `C:\DevProjects\risk_analysis_flagship\docs_global\bi\`.

---

## 2) Data sources (as produced by the project)
- **Credit – KPIs (daily, append):**  
  `docs_global/bi/credit/kpis_daily.csv`
- **Credit – Segment rollups (daily files):**  
  `docs_global/bi/credit/segment_rollups_*.csv` (one CSV per day; same columns)
- **Fraud – KPIs (daily, append):**  
  `docs_global/bi/fraud/kpis_daily.csv`
- **Fraud – Metrics (daily, append):**  
  `docs_global/bi/fraud/metrics_daily.csv`
- **Fraud – Drift detail (optional, by day):**  
  `docs_global/bi/fraud/raw/YYYY-MM-DD/drift_summary.csv` (only when non-empty)

**Conventions**
- `date` is ISO `YYYY-MM-DD`.
- Numbers are numeric (no thousands separators).
- New KPI fields may appear over time (wide table); Tableau will handle nulls.

---

## 3) Connect in Tableau (do this once)
1. Open **Tableau** → **Connect** pane (left).
2. Choose **Text file**:
   - Add `docs_global/bi/credit/kpis_daily.csv`.
   - Add `docs_global/bi/credit/segment_rollups_*.csv` by clicking **New Union… → Wildcard (automatic)** and entering `segment_rollups_*.csv`.
   - Add `docs_global/bi/fraud/kpis_daily.csv`.
   - Add `docs_global/bi/fraud/metrics_daily.csv` (optional).
3. (Optional drift detail) Add a **Folder** connection to `docs_global/bi/fraud/raw/` and **union** all nested `drift_summary.csv` files.
4. Save the workbook to:  
   `docs_global/bi/tableau/Risk_Analytics_seed.twb` (or `.twbx` if you prefer a packaged workbook).

---

## 4) Minimal sheets to validate data (keep it barebones)
- **Credit_EL_trend**: `date` (continuous) vs `el_total_today` (line).
- **Credit_PD_trend**: `date` vs `avg_pd_today`.
- **Fraud_precision_trend**: `date` vs `precision` (or the exact metric field name in `metrics_daily.csv`).
- **Segments_heatmap**: from segment rollups → `state` (or `grade`) vs `total_EL` (color/size).

If these render with multiple days, your schema is good. No styling needed now.

---

## 5) Calculated fields to add later (paste when you’re ready)
- **EL Δ vs 7-day**  
ZN([el_total_today]) - LOOKUP(ZN([el_total_today]), -7)
- **PD Δ vs 7-day**  
ZN([avg_pd_today]) - LOOKUP(ZN([avg_pd_today]), -7)
- **PSI Traffic Light (Credit)**  
IF [max_psi_today] >= 0.25 THEN "Red"
ELSEIF [max_psi_today] >= 0.10 THEN "Amber"
ELSE "Green"
END
- **Top-N by EL (Segments)**  
Use a table calc Rank on `SUM([total_EL])`, filter by parameter `N`.

---

## 6) Refresh routine (daily)
1. Run your daily flows (or scheduled tasks).  
2. If needed, run **BI: Export for Tableau (Today)** in VS Code tasks.  
3. Open the Tableau workbook → **Data > Refresh All**.  
4. Save (if `.twb`) or re-publish (if using Public).

---

## 7) Known pitfalls & quick fixes
- **Empty/0-byte files (e.g., drift_summary.csv):** expected on quiet days; Tableau just won’t show rows for that day.
- **Dates show as strings:** In Tableau, change data type of `date` to **Date** (calendar icon).
- **Numbers treated as text:** In Tableau, change data types to **Number (Whole)** or **Number (Decimal)**.
- **Wildcard union didn’t pick up new days:** Click **Data Source** tab → **Refresh** or re-open workbook.
- **Performance:** If the CSVs grow, switch to **Extract** mode inside Tableau for faster rendering.

---

## 8) Optional later hardening (when you do the BI pass)
- Add field **aliases** (friendly names) in Tableau.
- Create **PSI traffic-light legend**, **delta badges**, **Top-N parameter**.
- Group dashboards: **Credit Overview**, **Credit Segments**, **Fraud Operational**, **Fraud Performance**.
- Consider a lightweight **schema contract**: a JSON of expected columns; on export, add missing columns as nulls so Tableau schema stays stable.

---

## 9) Done criteria for BI integration
- Workbook opens with no connection errors.
- Four minimal sheets render with multiple dates.
- Daily refresh shows updated values without manual schema fixes.


