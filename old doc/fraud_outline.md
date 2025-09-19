# Fraud Detection Project — Outline

## Scope & Objectives
- Detect and triage fraudulent transactions.
- Combine rule-based detection with ML scoring.
- Handle both batch (daily) and streaming (real-time) ingestion.
- Deliver dashboards and daily reports for fraud monitoring.
- Emphasize recall (catch fraud) while controlling false positives.

## Dataset Options
- Kaggle Credit Card Fraud dataset (~284k transactions).
- PaySim mobile money fraud simulation dataset (millions of rows).
- Simulated datasets with injected anomalies.

## Deliverables
- Clean dataset & SQL queries for transaction analysis.
- ML models (XGBoost/LightGBM).
- Rules engine (YAML-based).
- FastAPI scoring service (real-time).
- Monitoring dashboards & daily reports.
- Governance artifacts (model cards, rules changelog).
