# Runbook — Fraud A/B Evaluation & Promotion

## Inputs
- Candidate model (MLflow run), current ruleset version.

## Steps
1. Offline A/B: compare PR-AUC, recall@k, FPR@k; check latency.
2. Business impact: projected manual review load vs catch rate.
3. If better, prepare release note (model card “Change Log”).

## Promote
1. Write new artifact; update `fraud_detection_system/models/PROD_POINTER.txt`.
2. Ensure `docs/model_cards/fraud_model.md` updated in same commit.
3. Bump `fraud_detection_system/rules/CHANGELOG.md` if rules changed.

## Verify
- `/health` shows new model ts; run smoke `/score` with known fixtures.
