# Runbook — Fraud PROD Rollback

## When
- Hotfix needed due to precision/latency regressions.

## Steps
1. Open previous PROD artifact path from `docs_global/audits/<date>/fraud/PROD_POINTER.txt` or repo history.
2. Replace contents of `fraud_detection_system/models/PROD_POINTER.txt` with previous path.
3. Commit: `hotfix: rollback fraud prod pointer to <artifact>`
4. Verify: `/health` + one `/score` test vector; note rollback in audit notes.

## Follow-up
- Root-cause analysis and update model card “Change Log”.
