#!/usr/bin/env python
"""
Stage 2 Health Checks (minimal)
- Credit: income_to_loan_ratio > 0 (non-null)
- Fraud (batch): user_txn_count_day >= 0 and user_txn_amount_day >= 0
- Fraud (merchant): merchant_chargeback_rate in [0,1]
- Fraud (stream): rolling_amount_last_1h >= 0 (non-null rows)
"""
from pathlib import Path
import sys
import pandas as pd
import numpy as np

def _read_any(path_parquet: Path):
    try:
        return pd.read_parquet(path_parquet)
    except Exception:
        csv = path_parquet.with_suffix(".csv")
        if csv.exists():
            return pd.read_csv(csv)
        raise

def check_credit():
    p = Path("credit_scoring_system/data/featurestore/credit_features.parquet")
    if not p.exists() and not p.with_suffix(".csv").exists():
        raise AssertionError(f"Credit features not found at {p}")
    df = _read_any(p)

    # income_to_loan_ratio > 0 for non-null entries
    s = pd.to_numeric(df["income_to_loan_ratio"], errors="coerce")
    bad = s.dropna() <= 0
    if bad.any():
        raise AssertionError(f"Credit check failed: {bad.sum()} rows have income_to_loan_ratio <= 0")

def check_fraud_batch():
    # user daily velocity
    p_user = Path("fraud_detection_system/data/features_batch/user_daily_velocity.parquet")
    if not p_user.exists() and not p_user.with_suffix(".csv").exists():
        raise AssertionError("Fraud user_daily_velocity not found.")
    u = _read_any(p_user)

    # counts and amounts must be >= 0
    if (u["user_txn_count_day"] < 0).any():
        raise AssertionError("Fraud check failed: negative user_txn_count_day found.")
    if (pd.to_numeric(u["user_txn_amount_day"], errors="coerce") < 0).any():
        raise AssertionError("Fraud check failed: negative user_txn_amount_day found.")

    # merchant chargeback rate in [0,1] if file exists
    p_merch = Path("fraud_detection_system/data/features_batch/merchant_chargeback_rate.parquet")
    if p_merch.exists() or p_merch.with_suffix(".csv").exists():
        m = _read_any(p_merch)
        if not m.empty and "merchant_chargeback_rate" in m.columns:
            r = pd.to_numeric(m["merchant_chargeback_rate"], errors="coerce")
            bad = (r < 0) | (r > 1)
            if bad.any():
                raise AssertionError(f"Fraud check failed: {bad.sum()} merchant_chargeback_rate outside [0,1].")

def check_fraud_stream():
    p_stream = Path("fraud_detection_system/data/features_stream/stream_features.parquet")
    if not p_stream.exists() and not p_stream.with_suffix(".csv").exists():
        raise AssertionError("Fraud stream_features not found.")
    s = _read_any(p_stream)

    if "rolling_amount_last_1h" in s.columns:
        vals = pd.to_numeric(s["rolling_amount_last_1h"], errors="coerce")
        bad = vals.dropna() < 0
        if bad.any():
            raise AssertionError(f"Fraud stream check failed: {bad.sum()} rows have rolling_amount_last_1h < 0")

def main():
    check_credit()
    check_fraud_batch()
    check_fraud_stream()
    print("✅ ALL HEALTH CHECKS PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
