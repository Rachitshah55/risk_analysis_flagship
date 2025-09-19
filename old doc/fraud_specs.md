# Fraud Detection Project — Specs

## Pipeline Layers
- **Data Validation**: Great Expectations (schema, enums, temporal checks).
- **Feature Engineering**: Batch profiles (velocity, chargeback rate), streaming features (rolling sums, device stability).
- **Rules Engine**: YAML-based heuristic rules.
- **ML Model**: XGBoost/LightGBM with class imbalance handling.
- **Scoring Service**: FastAPI endpoint `/score`, versioned logs.
- **Monitoring**: Precision, recall, FPR, PSI drift detection.
- **Retraining**: Weekly or drift-triggered; MLflow registry promotion with approvals.
- **Reporting**: Daily HTML/PDF summaries, dashboards (Power BI/Tableau).
- **Orchestration**: Prefect or n8n workflows.
- **Governance**: Model cards, rules changelog, CI/CD checks.

## Suggested Directory
- `/data/raw/`, `/data/features_batch/`, `/data/features_stream/`, `/rules/`, `/models/`, `/monitoring/`, `/reports/`, `/docs/model_cards/`.
