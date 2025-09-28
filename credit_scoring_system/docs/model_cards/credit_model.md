# Model Card — Credit Risk Scoring (Stage 3 Baseline)

**Owner:** Risk Analytics  
**System:** Credit Risk Scoring  
**Approval:** Stage 3 — Baseline (not for production)  
**MLflow Experiment:** `credit_stage3_models`  
**Last Updated:** <YYYY-MM-DD HH:MM local>

---

## 1) Overview
- **Purpose:** Estimate borrower Probability of Default (PD) for portfolio risk and Expected Loss (EL = PD × LGD × EAD) rollups.
- **Intended use:** Internal analytics, monitoring, and future model iteration. Not approved for production decisions.
- **Out of scope:** Adverse-action notices, regulatory reporting, and automated approvals/declines.

---

## 2) Data Snapshot
- **Source windows:** <start_date> → <end_date> (state clearly; e.g., “2019-01-01 to 2021-12-31”).
- **Sample size (train/valid/test):** <n_train>/<n_valid>/<n_test>.
- **Class balance (default=1):**
  - Train: <pct%>
  - Valid: <pct%>
  - Test:  <pct%>
- **Sampling/filters:** <any filters, e.g., active loans only, min history, etc.>
- **Known biases:** <portfolio skew, thin-file borrowers, geographic gaps, etc.>

> Tip to fill quickly (Explorer → Right-click → “Run Python File in Terminal”):
> ```
> # shared_env/scripts/_card_helpers_credit.py (optional helper)
> import pandas as pd, json, sys, pathlib as p
> ROOT = p.Path(__file__).resolve().parents[2]
> # Adjust these paths to your actual cached splits if needed:
> for split in ["train","valid","test"]:
>     dfp = ROOT/"credit_scoring_system"/"data"/f"{split}.parquet"
>     if dfp.exists():
>         df = pd.read_parquet(dfp)
>         y = df["default"].astype(int)
>         print(split, "n=",len(y),"positives=",y.sum(),"pct=",round(100*y.mean(),2))
> # Features from latest model:
> latest = sorted((ROOT/"credit_scoring_system"/"models").glob("credit_*"))[-1]
> feats = json.loads((latest/"feature_list.json").read_text())
> print("feature_count=",len(feats))
> print("top_examples=", feats[:10])
> ```
> Paste the outputs into this section.

---

## 3) Features Used (Stage 3)
- Source of truth: `models/credit_YYYYmmdd_HHMMSS/feature_list.json`.
- Common examples (not exhaustive):
  - `income_to_loan_ratio`
  - `num_past_delinquencies`
  - `credit_utilization_pct`
  - plus engineered aggregates at borrower level (see feature store docs).

---

## 4) Modeling
- **Baseline models:** 
  - Logistic Regression (calibrated) → `logreg_calibrated.joblib`
  - XGBoost candidate → `xgb_model.joblib`
- **Target:** `default` (0/1).
- **Imbalance handling:** class_weight or scale_pos_weight (XGB).
- **Validation:** train/valid/test split with fixed seed.
- **Tracking:** parameters/metrics logged to MLflow experiment `credit_stage3_models`.

---

## 5) Performance (Stage 3 numbers, illustrative placeholders)
- **AUC (valid/test):** <0.00>/<0.00>
- **KS (valid/test):** <0.0>/<0.0>
- **Calibration (slope/intercept):** <0.00>/<0.00>
- **Top features (SHAP or coefficients):** <list 5–10>

(Attach plots or references to artifacts if generated: ROC, KS, calibration, SHAP summary.)

---

## 6) Assumptions & Limits
- Data quality meets Stage 2 checks; no severe drift vs. training window.
- Macroeconomic regime stability assumed; **not** stress-tested in Stage 3.
- Thin-file borrowers, recent credit events, or novel products may be poorly estimated.
- **Not production-ready**: monitoring thresholds and governance gates incomplete.

---

## 7) Ethical & Regulatory Considerations
- Avoid proxy features for protected attributes (race, religion, etc.).  
- Provide explainability (coefficients/SHAP) for any manual review usage.  
- Retain data minimum necessary; follow retention & privacy policies.

---

## 8) Operationalization Notes
- **Artifacts (success criteria):**  
  `credit_scoring_system/models/credit_YYYYmmdd_HHMMSS/{logreg_calibrated.joblib, xgb_model.joblib, feature_list.json}`
- **Dependencies:** Python, pandas, scikit-learn, xgboost, MLflow.
- **Next:** Stage 4 scoring + EL rollups; Stage 5 monitoring; Stage 8 governance gates.

---

## 9) Approval
- **Status:** Stage 3 — Baseline (not for production)  
- **Reviewed by:** <name/date>  
- **Notes:** For analysis and iteration only.


---
## Appendix — Original Auto-Generated Stub
```json
{
  "model_family": "credit_pd",
  "timestamp": "20250926_185132",
  "training": {
    "train_class_counts": {
      "1": 3,
      "0": 1
    },
    "test_class_counts": {
      "1": 1,
      "0": 1
    },
    "lr_calibration": "Uncalibrated (minority count=1)"
  },
  "metrics": {
    "auc_lr": 0.0,
    "ks_lr": 0.0,
    "auc_xgb": 0.5,
    "ks_xgb": 0.0
  },
  "notes": "Stage 3 baseline models. Data: borrower-level engineered features; label aggregated from loans."
}
```