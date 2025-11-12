This file consolidates the previous project outline.md, roadmap.md, specs.md, and dashboard.md into a single, comprehensive document. The original four files are now deprecated and their content has been migrated here.

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


# Credit Risk Scoring Project — Roadmap (Expanded)

## Stages in Detail

### Stage 1: Ingestion & Validation
- Load loan datasets (CSV, SQL, API). Store in `data/raw/`.
- GE validation suites: schema checks, missing values, ranges (loan_amount > 0).

### Stage 2: Transformation & Feature Engineering
- Use dbt or pandas to build borrower-level features:
  - Income-to-loan ratio.
  - Number of past delinquencies.
  - Credit utilization percentage.
- Store in `data/featurestore/`.

### Stage 3: Model Development
- Logistic regression (baseline, interpretable).
- XGBoost candidate (higher predictive power).
- Metrics: AUC, KS, Gini, calibration slope.
- MLflow experiment tracking.

### Stage 4: Batch Scoring
- Compute PD per borrower.
- Expected Loss = PD × LGD × EAD.
- Segment rollups (by geography, grade, vintage).

### Stage 5: Monitoring
- Calibration drift detection with Evidently.
- PSI for key borrower segments (income, grade).

### Stage 6: Reporting
- Monthly HTML reports via nbconvert.
- Include SHAP plots, PD distribution, EL by segment.

### Stage 7: Automation
- Prefect/n8n monthly orchestration flow:
  - Ingest → Validate → Transform → Train → Score → Report.

### Stage 8: Governance
- Model cards in `/docs/model_cards/`.
- CI/CD checks via GitHub Actions (unit tests, validation).

## End Product
- Automated pipeline producing PD + EL monthly with dashboards and audit-ready documentation.


# Credit Risk Scoring Project — Specs (Expanded)

## Pipeline Layers
1. **Data Contracts & Validation**
   - GE expectations: loan_amount > 0, credit_history ∈ {0,1}, employment_length ∈ [0,40].
   - Validation reports saved to `/docs/validation/`.

2. **Transformations**
   - dbt SQL models or pandas transformations.
   - Feature engineering examples:
     ```sql
     SELECT borrower_id,
            SUM(late_payments) AS total_lates,
            AVG(income/loan_amount) AS income_loan_ratio
     FROM loans
     GROUP BY borrower_id;
     ```

3. **Model Training**
   - Logistic regression with WOE binning.
   - XGBoost with hyperparameter tuning (Optuna/RandomizedSearch).
   - MLflow logging for metrics + parameters.

4. **Model Registry**
   - Staging vs Production tags.
   - Manual promotion process.

5. **Batch Scoring**
   - Script to compute PD + EL by borrower.
   - Store results in `outputs/`.

6. **Monitoring**
   - Evidently drift detection (PSI > 0.25 → trigger retrain).
   - Calibration slope < 0.9 → alert.
   - scheduled daily from Stage 5

7. **Reporting**
   - Monthly risk reports with KPIs.
   - Monthly reports aggregate daily monitoring outputs.
   - Portfolio breakdown tables.

8. **Governance**
   - Model card with methodology, metrics, limitations.
   - GitHub Actions test pipeline.

## Directory Example
```
data/raw/
data/featurestore/
models/
reports/
docs/model_cards/
```

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

