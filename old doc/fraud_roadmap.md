# Fraud Detection Project — Roadmap

## Stages
1. **Ingestion & Validation**: Load datasets, validate schema and labels.
2. **Feature Engineering**: Batch profiles + simulated streaming features.
3. **Model + Rules**: Train ML models, combine with YAML rules.
4. **Scoring API**: FastAPI service, logs versioned decisions.
5. **Monitoring**: Evidently for drift + performance, alerts on breaches.
6. **Retraining & A/B Testing**: Candidate shadow deployment, promotion gates.
7. **Reporting**: Daily reports, dashboards with fraud patterns.
8. **Automation**: Prefect/n8n orchestrated jobs (batch + stream).
9. **Governance**: Model cards, rules changelog, CI/CD.

## End Product
- Real-time + batch fraud detection platform with monitoring and governance.
