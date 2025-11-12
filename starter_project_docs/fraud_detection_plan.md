This file consolidates the previous project outline.md, roadmap.md, specs.md, and dashboard.md into a single, comprehensive document. The original four files are now deprecated and their content has been migrated here.

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


# Fraud Detection Project — Specs (Expanded)

## Pipeline Layers
1. **Validation**
   - GE checks: transaction amount > 0, valid enums, timestamps monotonic.
   - Example config:
     ```yaml
     expectations:
       - amount > 0
       - transaction_type in {PAYMENT, CASH_OUT, TRANSFER}
     ```

2. **Feature Engineering**
   - Batch: profiles of user, merchant, device.
   - Streaming: rolling velocity, geolocation mismatch.

3. **Rules Engine**
   - `rules_v1.yml` example:
     ```yaml
     - name: High Amount, New Account
       condition: amount > 5000 and account_age < 30
       action: flag
     ```

4. **Model Training**
   - XGBoost with class imbalance weights.
   - Metrics: precision, recall, ROC AUC.
   - MLflow logging.

5. **Scoring API**
   - FastAPI `/score` endpoint.
   - Logs decision, SHAP explanation.

6. **Monitoring**
   - Drift: PSI > 0.2 triggers alert.
   - Performance: precision < 0.85 triggers retrain.

7. **Retraining**
   - Weekly pipeline or on drift.
   - Candidate model shadow tested.

8. **Reporting**
   - Daily HTML report.
   - Tableau dashboard with fraud attempts, fraud prevented.

9. **Governance**
   - Model cards: `/docs/model_cards/fraud_model.md`.
   - Rules changelog.

## Directory Example
```
data/raw/
data/features_batch/
data/features_stream/
rules/
models/
monitoring/
reports/
docs/model_cards/
```

# Fraud Detection Project — Dashboard & Reporting (Expanded)

## Dashboards (Tableau)
1. **Operational View**
   - Transactions flagged per rule.
   - Queue size for investigators.
   - SLA on review times.

2. **Risk View**
   - Fraud prevented ($).
   - Geo heatmaps of fraud attempts.
   - SHAP feature insights.

3. **Performance Trends**
   - Precision, recall, FPR over time.
   - Latency distribution.

## Reports (HTML/PDF)
- **Daily Report Contents**:
  1. Summary of fraud incidents.
  2. Model precision, recall, FPR.
  3. Drift analysis plots.
  4. Candidate vs production A/B comparison.
  5. Governance appendix.

## Example KPIs
- Recall = 92% (fraud caught).
- False positive rate = 3%.
- Fraud prevented = $2.1M over last 30 days.

