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

