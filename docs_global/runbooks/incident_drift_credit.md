# Runbook — Credit Drift Incident

## Trigger
- Evidently PSI ≥ threshold (warn/error) or alert email fired.

## Triage (Owner)
1. Open latest: `docs_global/monitoring/credit/<YYYY-MM-DD>/`
2. Review `drift_report.html` + calibration plot.
3. Check data-contract changes (schema, ranges) in recent ingest.

## Decision
- **Benign source shift?** Adjust thresholds or features (doc in model card change log).
- **Material shift?** Retrain candidate and A/B offline.

## Actions
1. If proceeding to retrain, log intent in `docs/model_cards/credit_model.md` (“Change Log”).
2. Train, record MLflow run ID, validate.
3. Update PROD pointer only after sign-off.

## Sign-off
- Owner → Risk Lead → Release Manager (use `APPROVALS_TEMPLATE.md`).
