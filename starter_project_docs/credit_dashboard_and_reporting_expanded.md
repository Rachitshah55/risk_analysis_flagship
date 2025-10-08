# Credit Risk Scoring Project — Dashboard & Reporting (Expanded)

## Dashboards (Tableau)
1. **Portfolio Risk Overview**
   - Total outstanding balance.
   - Distribution of PD (histogram).
   - Exposure by grade, geography, segment.

2. **Expected Loss Analysis**
   - EL by segment.
   - Stress-test toggles for macro scenarios.

3. **Model Performance**
   - ROC curve, AUC, KS.
   - Calibration plots over time.

4. **Risk Trends**
   - New defaults vs recoveries.
   - Delinquency rate trends.

## Reports (HTML/PDF)
- Monthly risk report template:
- Credit monitoring is daily (Stage 5); this report summarizes monthly.
  1. **Executive Summary** (portfolio risk snapshot).
  2. **Model Performance** (AUC, KS, calibration).
  3. **Segment Analysis** (by grade, geography).
  4. **Stress Testing** results.
  5. **Appendices**: validation reports, SHAP plots.

## Example KPIs
- Average PD = 3.4%.
- EL (USD) = $1.2M.
- Drift in credit utilization = PSI 0.35 → retrain triggered.

