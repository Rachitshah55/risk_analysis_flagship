
import os, mlflow

uri = os.getenv("MLFLOW_TRACKING_URI") or "file:///C:/DevProjects/risk_analysis_flagship/mlruns"
mlflow.set_tracking_uri(uri)
mlflow.set_experiment("risk_flagship")  # creates it if missing

print("TRACKING_URI =", uri)
with mlflow.start_run(run_name="smoke_setup_gui"):
    mlflow.log_param("ok", 1)
    mlflow.log_metric("m", 0.5)
print("Run created.")
