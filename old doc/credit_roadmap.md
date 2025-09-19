# Credit Risk Scoring Project — Roadmap

## Stages
1. **Ingestion & Validation**: Load datasets, validate with Great Expectations.
2. **Transformation**: dbt or pandas+SQL feature pipelines.
3. **Model Development**: Logistic regression + ML candidate, registered in MLflow.
4. **Batch Scoring**: Compute PD, EL, portfolio rollups.
5. **Monitoring**: Drift detection, calibration monitoring with Evidently.
6. **Reporting**: Auto-generated reports, BI dashboards.
7. **Automation**: Prefect/n8n orchestration, scheduled monthly runs.
8. **Governance**: Model cards, GitHub Actions CI/CD, reproducibility.

## End Product
- Fully automated monthly pipeline with governance and dashboards.
