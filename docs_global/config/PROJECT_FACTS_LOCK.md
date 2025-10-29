# Project Facts — LOCK (Stage 9)

- Credit cadence: **Daily is primary**. Monthly outputs are derived EOM roll-ups from daily snapshots.
- Fraud stack: **Model + Rules** (ruleset v1.0.0) behind FastAPI `/score`, with PROD pointer guard.
- Monitoring: Daily credit PSI/calibration and fraud latency/drift; alerts routed via Gmail API bridge.
- Governance: CI gate blocks merges without rules changelog bumps, model-card refresh on model changes, and audit pack on release branches/tags.
