
# Model Card — Fraud Detection (Stage 3 Model + Rules)

**Owner:** Risk Analytics  
**System:** Fraud Detection (Batch + Stream)  
**Approval:** Stage 3 — Baseline (not for production)  
**MLflow Experiment:** `fraud_stage3_model_and_rules`  
**Last Updated:** <YYYY-MM-DD HH:MM local>

---

## 1) Overview
- **Purpose:** Detect likely fraudulent transactions using a **combined decision** = ML model score + YAML rules.
- **Intended use:** Internal evaluation, rules refinement, and incident triage testing. Not approved for production blocking.
- **Out of scope:** Automated customer actions (declines, holds) without human-in-the-loop review.

---

## 2) Data Snapshot
- **Source windows:** <start_date> → <end_date>.
- **Sample size (train/valid/test):** <n_train>/<n_valid>/<n_test>.
- **Class balance (fraud=1):**
  - Train: <pct%>
  - Valid: <pct%>
  - Test:  <pct%>
- **Sampling/filters:** e.g., payments/transfers only, min activity history, device dedup.
- **Known biases:** merchant type skew, geo coverage limits, synthetic injections.

> Quick helper (optional) mirroring the credit script:
> ```
> # shared_env/scripts/_card_helpers_fraud.py
> import pandas as pd, json, sys, pathlib as p
> ROOT = p.Path(__file__).resolve().parents[2]
> for split in ["train","valid","test"]:
>     dfp = ROOT/"fraud_detection_system"/"data"/f"{split}.parquet"
>     if dfp.exists():
>         df = pd.read_parquet(dfp)
>         y = df["is_fraud"].astype(int)
>         print(split, "n=",len(y),"positives=",y.sum(),"pct=",round(100*y.mean(),3))
> latest = sorted((ROOT/"fraud_detection_system"/"models").glob("fraud_*"))[-1]
> feats = json.loads((latest/"feature_list.json").read_text())
> thr = json.loads((latest/"threshold.json").read_text())["threshold"]
> print("feature_count=",len(feats),"threshold=",thr)
> print("top_examples=", feats[:10])
> ```

---

## 3) Features & Rules (Stage 3)
- **Features** (see `feature_list.json` in latest model directory). Common examples:
  - `rolling_amount_last_1h`, `avg_amount_user`, `account_age_days`
  - `device_change_count_day`, `geo_location_mismatch`, `merchant_chargeback_rate`
- **Rules (YAML):** `fraud_detection_system/rules/rules_v1.yml`  
  Examples:
  - High Amount, New Account → `amount > 5000 and account_age_days < 30`
  - Velocity Spike → `rolling_amount_last_1h > 3 * avg_amount_user`
  - Cross-Border at Odd Hours → <your rule>

---

## 4) Modeling & Decisioning
- **Model:** XGBoost with class-imbalance handling (scale_pos_weight).  
- **Decision:** 
  - `flag = (model_proba >= threshold) OR (any_rule_fired == True)`  
  - `threshold` stored in `threshold.json` (validated in Stage 3 health check).
- **Validation:** train/valid/test split with fixed seed.  
- **Tracking:** parameters/metrics logged to MLflow experiment `fraud_stage3_model_and_rules`.

---

## 5) Performance (Stage 3 placeholders)
- **Precision / Recall (valid/test):** <p>/<r>  
- **ROC AUC (valid/test):** <0.00>/<0.00>  
- **FPR / Latency targets:** <fpr%>, <p50/p95 ms> (if measured)  
- **Top SHAP features:** <list 5–10>  
- **Rules impact:** % of flags due to rules, incremental recall vs model alone.

---

## 6) Assumptions & Limits
- Event timestamps valid and monotonic (Stage 2 check).  
- Streaming features computed within SLA; windowing correct on timezone.  
- Threshold tuned on validation; may drift with new campaigns/seasons.  
- High-risk periods (promos/holidays) not yet separately tuned.

---

## 7) Ethical & Operational Considerations
- False positives → user friction; require investigator review workflow.  
- Appeals & auditability: retain decision trace (rules fired, SHAP top factors).  
- Geo and device-based features can embed socio-economic signals; use carefully.

---

## 8) Operationalization Notes
- **Artifacts (success criteria):**  
  `fraud_detection_system/models/fraud_YYYYmmdd_HHMMSS/{xgb_model.joblib, threshold.json, feature_list.json}`  
- **Rules:** `fraud_detection_system/rules/rules_v1.yml`  
- **API (future):** Stage 4 FastAPI `/score` to return `{flag, model_proba, rules_fired, shap_top}`.

---

## 9) Approval
- **Status:** Stage 3 — Baseline (not for production)  
- **Reviewed by:** <name/date>  
- **Notes:** Proceed to monitoring + API work before any production trial.

---
## Appendix — Original Auto-Generated Stub
```json
{
  "model_family": "fraud_txn",
  "timestamp": "20250927_114752",
  "metrics": {
    "auc": 1.0,
    "precision_thr": 1.0,
    "recall_thr": 1.0,
    "precision_combined": 1.0,
    "recall_combined": 1.0
  },
  "notes": "Stage 3 baseline XGB + YAML rules. Threshold chosen for recall. Timestamp guard prevents stale features."
}
```