import os, json, time, joblib
import numpy as np
from xgboost import XGBClassifier

# Where to write the new artifact
ROOT = r"C:\DevProjects\risk_analysis_flagship\credit_scoring_system\models"
stamp = time.strftime("credit_%Y%m%d_%H%M%S")
OUT = os.path.join(ROOT, stamp)
os.makedirs(OUT, exist_ok=True)

# Your 4 features (same names the API expects)
features = ["income_to_loan_ratio", "num_past_delinquencies", "credit_utilization_pct", "n_records"]

# ---- synth training data with real spread ----
rng = np.random.default_rng(42)
n = 5000
X = np.zeros((n, 4), dtype=float)
X[:,0] = rng.uniform(0.1, 6.0, n)   # income_to_loan_ratio
X[:,1] = rng.integers(0, 6, n)      # num_past_delinquencies
X[:,2] = rng.uniform(0.01, 0.98, n) # credit_utilization_pct
X[:,3] = rng.integers(1, 72, n)     # n_records

# nonlinear-ish label: higher PD when ratio low, delinq high, util high, short history
logit = (
    -1.2 * (X[:,0] - 1.5) + 
     0.9 * X[:,1] +
     2.0 * (X[:,2] - 0.4) +
    -0.02 * (X[:,3] - 12)
)
p = 1 / (1 + np.exp(-logit))
y = (rng.uniform(0,1,n) < p).astype(int)

# ---- small XGB model that will vary by features ----
clf = XGBClassifier(
    n_estimators=120,
    max_depth=3,
    learning_rate=0.08,
    subsample=0.9,
    colsample_bytree=0.9,
    reg_lambda=1.0,
    objective="binary:logistic",
    eval_metric="logloss",
    n_jobs=2,
    random_state=42,
)
clf.fit(X, y)

# ---- write artifacts with the same filenames your API expects ----
joblib.dump(clf, os.path.join(OUT, "xgb_model.joblib"))
with open(os.path.join(OUT, "feature_list.json"), "w", encoding="utf-8") as f:
    json.dump({"numeric_features": features}, f, indent=2)
with open(os.path.join(OUT, "threshold.json"), "w", encoding="utf-8") as f:
    json.dump({"pd_threshold": 0.20}, f, indent=2)

print("[OK] Published:", OUT)
