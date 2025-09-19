# Shared Overview (Expanded)

## Vision & Goals
The goal of this initiative is to build **two flagship projects** that demonstrate advanced risk analytics capabilities:

1. **Credit Risk Scoring Model**  
   - Predict borrower default probability (Probability of Default, PD).  
   - Automate Expected Loss (EL) and IFRS9/CECL compliance metrics.  
   - Build dashboards for portfolio analysis.  

2. **Fraud Detection System**  
   - Detect suspicious transactions in real-time (streaming) and batch.  
   - Combine machine learning with a rules-based detection engine.  
   - Build operational dashboards and automated reports.  

Both projects must:  
- **Minimize manual work** → pipelines handle ingestion, validation, scoring, reporting.  
- **Maximize governance & trust** → everything auditable and reproducible.  
- **Highlight explainability** → business/regulators must understand why a score/decision was made.  

## Shared Methodologies
### Data Pipeline
- **Ingestion**: Pull datasets from S3, Postgres, or local CSVs. Store raw copies.  
- **Validation**: Great Expectations checks schema, ranges, and distributions.  
- **Transformation**: dbt or pandas pipelines for feature engineering.  
- **Modeling**: MLflow for experiments, tracking, and registry.  
- **Scoring**: Batch jobs or API endpoints.  
- **Monitoring**: Evidently for drift; SHAP for explainability.  
- **Reporting**: Jupyter → nbconvert → PDF/HTML; dashboards in Tableau/Power BI.  

### Automation & Orchestration
- **Prefect or n8n** for scheduling and dependency management.  
- **CI/CD via GitHub Actions** to run validations, unit tests, and training jobs.  
- **Version control with Git + DVC** for code and data snapshots.  

### Governance
- **Model cards** describe training data, methodology, metrics, limitations.  
- **Rules changelog** for fraud system.  
- **Audit logs** → every run linked to a Git commit + data hash.  

## Shared Tech Stack
- **Python stack**: pandas, scikit-learn, XGBoost, LightGBM, SHAP.  
- **Validation**: Great Expectations.  
- **Data transformation**: dbt, SQL.  
- **Tracking/versioning**: MLflow, DVC, GitHub.  
- **Monitoring**: Evidently, SHAP, Prometheus/Grafana optional.  
- **APIs**: FastAPI (fraud real-time).  
- **Visualization**: Tableau, Power BI.  

## Governance Principles
- **Reproducibility**: Any month/day’s run can be regenerated exactly (via Git+DVC+MLflow).  
- **Approvals**: No model goes to production without manual risk review.  
- **Explainability**: Every prediction has interpretable evidence (coefficients or SHAP).  
- **Audit-ready**: Reports, dashboards, and model cards stored with version tags.  
