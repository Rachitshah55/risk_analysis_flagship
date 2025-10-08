# Shared Roadmap (Expanded)

This roadmap aligns both projects while keeping them modular.

## Setup & Foundations (Common)
- **Root structure**:  
  ```
  C:\DevProjects\risk_analysis_flagship\
     ├── credit_scoring_system\
     ├── fraud_detection_system\
     ├── shared_env\
     └── docs_global\
  ```

- **Environment setup**: Python venv, installs (pandas, scikit-learn, MLflow, DVC, Prefect, GE, Evidently).  
- **Repos**: Git init, DVC init, MLflow tracking directory.  
- **Validation dry run**: sample dataset, one GE expectation.  

## Credit Risk Project Stages
1. Ingestion & validation (monthly data).  
2. Transformation (dbt + SQL).  
3. Model training (logistic regression + XGBoost).  
4. Scoring portfolio → PD + Expected Loss.  
5. runs daily from Stage 5 to Monitoring with Evidently (AUC, calibration, PSI drift).  
6. Reporting → nbconvert reports + Power BI dashboards.  
7. Automation via Prefect: daily monitoring Flows, monthly reporting Flow.  
8. Governance (model card, CI/CD gates).  

## Fraud Detection Project Stages
1. Ingestion & validation (daily/stream).  
2. Feature engineering (batch profiles + streaming features).  
3. Model + rules combined scoring.  
4. FastAPI scoring service (real-time).  
5. Monitoring (precision, recall, drift).  
6. Retraining & A/B testing with MLflow promotion.  
7. Daily reporting + Power BI dashboards.  
8. Orchestration (Prefect/n8n flows).  
9. Governance (model card, rules changelog).  

## Tracking Framework
- **Credit**: checkpoints at ingestion, model registry, scoring outputs, monitoring dashboards, governance artifacts.  
- **Fraud**: checkpoints at ingestion, feature store, API deployment, monitoring alerts, retraining, governance.  

✅ **End Result**: Both projects fully automated, governed, and reproducible.  
