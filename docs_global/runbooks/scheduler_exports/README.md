# Scheduler Exports

Import these via Task Scheduler → Task Scheduler Library → Action: Import Task…
- credit_daily_flow.xml  (runs shared_env\monitoring\run_credit_daily_full.py)
- fraud_daily_flow.xml   (runs shared_env\monitoring\run_fraud_daily_full.py)
- monthly_credit_rollup.xml (runs shared_env\monitoring\monthly_credit_rollup_flow.py)

After import, edit “Start in (optional)” to: `C:\DevProjects\risk_analysis_flagship`
