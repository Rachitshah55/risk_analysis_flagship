# Fraud Detection Project — Outline (Expanded)

## Scope & Objectives
- Build a fraud detection system for transactions.
- Support batch (daily) + real-time (streaming) scoring.
- Use machine learning and business rules together.
- Provide dashboards and daily reports for monitoring.

## Business Impact
- Fraud losses = direct financial hit + reputational risk.
- False positives → customer friction + investigation overhead.
- Goal: maximize recall (catch frauds) with controlled false positives.

## Dataset Options
- **Kaggle Credit Card Fraud** (~284k transactions, 0.17% fraud).  
- **PaySim Mobile Money Simulation** (millions of transactions, labeled frauds).  
- **Synthetic injections**: anomalous transactions added to normal logs.

## Deliverables
- Ingestion pipeline + GE validation.
- Feature engineering (velocity, device stability, geo anomalies).
- ML model (XGBoost, LightGBM).
- Rules engine (YAML config).
- FastAPI scoring service.
- Dashboards (Power BI, Tableau).
- Daily reports (HTML/PDF).
- Governance docs (model cards, rules changelog).

