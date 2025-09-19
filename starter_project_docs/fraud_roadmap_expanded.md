# Fraud Detection Project — Roadmap (Expanded)

## Stages in Detail

### Stage 1: Ingestion & Validation
- Load raw dataset → `data/raw/`.
- GE checks: schema, timestamp monotonicity, amount > 0.

### Stage 2: Feature Engineering
- Batch: historical profiles (user velocity, merchant chargeback rates).
- Streaming: rolling aggregates (amount last 1h, device changes).

### Stage 3: Model + Rules
- ML model: XGBoost with class weights.
- Rule engine: YAML rules like "amount > $5000 & account_age < 30 days".
- Decision = model_score + rules.

### Stage 4: Scoring API
- FastAPI `/score` endpoint.
- Input: transaction JSON.
- Output: fraud flag + SHAP top features.

### Stage 5: Monitoring
- Evidently for drift (amount distribution).
- Metrics: precision, recall, FPR, latency.

### Stage 6: Retraining & A/B Testing
- Retrain weekly or on drift triggers.
- Shadow deployment with 10% traffic.
- Promote via MLflow if metrics pass.

### Stage 7: Reporting & Dashboards
- Daily HTML report with fraud incidents.
- Power BI dashboard with fraud prevented.

### Stage 8: Automation
- Prefect/n8n pipeline: validate → features → score → monitor → report.

### Stage 9: Governance
- Model card + rules changelog in `/docs/`.
- CI/CD with GitHub Actions tests.

## End Product
- Real-time fraud detection API + dashboards + governance.

