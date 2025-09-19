# Credit Risk Scoring Project — Specs

## Pipeline Layers
- **Data Contracts & Validation**: Great Expectations, schema & range checks.
- **Transformations**: dbt SQL models, borrower snapshots, loan rollups, macro joins.
- **Model Training**: Logistic regression baseline, XGBoost candidate. Metrics: AUC, KS, calibration.
- **Model Registry**: MLflow for staging → production.
- **Batch Scoring**: Script to compute PD and Expected Loss, segment rollups.
- **Monitoring**: PSI drift detection, SHAP rank drift, calibration drift.
- **Reporting**: nbconvert reports, Tableau/Power BI dashboards.
- **Orchestration**: Prefect flows or n8n workflows.
- **Governance**: Model cards, DVC data versioning, CI/CD gates.

## Suggested Directory
- `/data/raw/`, `/data/featurestore/`, `/models/`, `/reports/`, `/docs/model_cards/`.
