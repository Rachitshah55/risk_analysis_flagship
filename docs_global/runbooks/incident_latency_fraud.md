# Runbook — Fraud API Latency/Errors

## Trigger
- p95 latency > SLO or HTTP 5xx spikes; alert email fired.

## Triage
1. Check API logs: `fraud_detection_system/api/logs/<YYYY-MM-DD>.jsonl`
2. Verify model artifact & PROD pointer present.
3. Inspect system load and recent deploys.

## Actions
- Roll back to previous PROD pointer if regression suspected.
- Scale or restart service (if deployed), purge noisy devices if applicable (ops note).

## Post-mortem
- Add a brief summary to audit pack notes; update thresholds if needed.
