# Shared Overview

## Vision & Goals
Two flagship risk analytics projects:
- **Credit Risk Scoring Model**: Predict borrower default probability and assess portfolio risk.
- **Fraud Detection System**: Detect and triage fraudulent transactions in real-time and batch.

Both projects share:
- Automation-first approach (minimal manual intervention).
- Enterprise-grade governance (auditability, reproducibility, monitoring).
- Emphasis on explainability for trust (SHAP, validation, transparency).

## Shared Methodologies
- **Pipelines**: Ingestion → Validation → Transformation → Model Training → Scoring → Monitoring → Reporting.
- **Automation**: Orchestrated flows with Prefect/n8n, CI/CD with GitHub Actions, reproducibility with Git+DVC.
- **Governance**: Model cards, rules changelog, approval workflows, audit trails.
- **Monitoring**: Evidently for drift/performance, SHAP for explainability, alerts to Slack/Jira.

## Shared Tech Stack
- **Languages**: Python, SQL.
- **ML Libraries**: scikit-learn, XGBoost, LightGBM, SHAP.
- **Data Tools**: pandas, NumPy, dbt, Great Expectations, DVC.
- **Orchestration**: Prefect, n8n.
- **Tracking & Versioning**: MLflow, GitHub, GitHub Actions.
- **Dashboards**: Tableau, Power BI.
- **APIs**: FastAPI (Fraud system real-time scoring).

## Governance Principles
- Every artifact versioned and reproducible (git tag + DVC hash).
- Clear approval gates for model promotion (MLflow staging → production).
- Documentation for regulators and business stakeholders (model cards, validation reports).
- Reproducibility as a non-negotiable feature: any historical report must be regenerable.
