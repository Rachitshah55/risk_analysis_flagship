# Fraud Detection Model — Model Card (Stage 9)

**Status:** Steady-state (governed)  
**Works with:** ruleset v1.0.0 + FastAPI /score

## Training & Data Snapshot
- Period: YYYY-MM-DD to YYYY-MM-DD
- Features (top): …
- Algo & version: …
- Class balance: …

## Performance (last train)
- ROC-AUC: …
- PR-AUC: …
- Latency p95 (API): …
- Threshold(s): …

## Monitoring Summary (last 14–30 days)
- Drift (inputs): …
- Latency: …
- Alerts: …

## Lineage & Evidence
- MLflow Run(s): …
- Artifact path: …

## Assumptions / Limits
- …

## Approvals
- Owner: __________  Date: ______
- Risk Lead: ______  Date: ______

## Change Log

### 2025-10-29 — PROD pointer update (pointer-only)
- Updated `fraud_detection_system/models/PROD_POINTER.txt` to a repo-relative path for CI portability:
  - **New pointer:** `models/CAND_20251014/`
  - **Old pointer:** local absolute Windows path (non-portable)
- No change to model weights, thresholds, or features. MLflow run unchanged.
- **Smoke evidence**: `/health` = 200; `/score` returns 200 with valid JSON.
- Approvals:
  - Owner: __________________  Date: __________
  - Risk Lead: ______________  Date: __________
  - Release Mgr: ____________  Date: __________
