# Credit Risk Scoring Project — Specs (Expanded)

## Pipeline Layers
1. **Data Contracts & Validation**
   - GE expectations: loan_amount > 0, credit_history ∈ {0,1}, employment_length ∈ [0,40].
   - Validation reports saved to `/docs/validation/`.

2. **Transformations**
   - dbt SQL models or pandas transformations.
   - Feature engineering examples:
     ```sql
     SELECT borrower_id,
            SUM(late_payments) AS total_lates,
            AVG(income/loan_amount) AS income_loan_ratio
     FROM loans
     GROUP BY borrower_id;
     ```

3. **Model Training**
   - Logistic regression with WOE binning.
   - XGBoost with hyperparameter tuning (Optuna/RandomizedSearch).
   - MLflow logging for metrics + parameters.

4. **Model Registry**
   - Staging vs Production tags.
   - Manual promotion process.

5. **Batch Scoring**
   - Script to compute PD + EL by borrower.
   - Store results in `outputs/`.

6. **Monitoring**
   - Evidently drift detection (PSI > 0.25 → trigger retrain).
   - Calibration slope < 0.9 → alert.
   - scheduled daily from Stage 5

7. **Reporting**
   - Monthly risk reports with KPIs.
   - Monthly reports aggregate daily monitoring outputs.
   - Portfolio breakdown tables.

8. **Governance**
   - Model card with methodology, metrics, limitations.
   - GitHub Actions test pipeline.

## Directory Example
```
data/raw/
data/featurestore/
models/
reports/
docs/model_cards/
```

