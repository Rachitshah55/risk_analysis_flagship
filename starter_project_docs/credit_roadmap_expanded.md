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

