# Credit Model Card (Stage 3 Baseline)

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