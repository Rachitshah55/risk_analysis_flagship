# Credit Risk Scoring Project — Outline (Expanded)

## Scope & Objectives
This project focuses on predicting borrower default risk and portfolio losses.  
Objectives include:
- Building Probability of Default (PD) models for individual borrowers.
- Automating Expected Loss (EL) and IFRS9/CECL compliance metrics.
- Creating dashboards for portfolio monitoring.
- Ensuring explainability and regulatory trust.

### Why This Matters
Credit risk models directly impact capital requirements for banks, loan approvals, and investor confidence.  
Regulators demand transparent, validated, and auditable models. Employers look for hands-on capability in this domain.

## Dataset Options
- **LendingClub Loan Data**: Millions of US consumer loans with performance outcomes.
- **Home Credit Default Dataset (Kaggle)**: Rich features on borrowers’ behavior and default flags.
- **Simulated Data**: 100k+ loans, synthetic macroeconomic features (GDP, unemployment).

## Deliverables
- **Data Pipeline**: ingestion, cleaning, validation (with Great Expectations).
- **EDA & Feature Engineering**: income-to-loan ratios, delinquency counts, macro features.
- **Models**: Logistic regression (scorecard), XGBoost/LightGBM candidate.
- **Explainability**: SHAP summary plots, feature importance, calibration checks.
- **Expected Loss Calculations**: PD × LGD × EAD rollups.
- **Dashboards**: Tableau/Power BI portfolio risk views.
- **Reports**: Monthly auto-generated HTML/PDF with model performance + portfolio KPIs.

