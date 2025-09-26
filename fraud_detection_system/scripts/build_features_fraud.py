#!/usr/bin/env python
from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd


# ---------- helpers ----------
def pick_col(df: pd.DataFrame, candidates: list[str], required: bool = False) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"Required column not found. Tried: {candidates}")
    warnings.warn(f"None of the columns found: {candidates}")
    return None


def ensure_datetime(s: pd.Series) -> pd.Series:
    if np.issubdtype(s.dtype, np.datetime64):
        return s
    return pd.to_datetime(s, errors="coerce")


# ---------- feature logic ----------
def compute_batch_features(
    df: pd.DataFrame,
    user_col: str,
    ts_col: str,
    amt_col: str,
    device_col: Optional[str],
    merchant_col: Optional[str],
    cb_flag_col: Optional[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      user_day (per-user per-day):
        [user_id, date, user_txn_count_day, user_txn_amount_day, device_change_count_day]
      merchant_rates (per-merchant overall):
        [merchant_id, txn_count, chargeback_count, merchant_chargeback_rate]
    """
    # Normalize timestamp -> date
    df["_date"] = pd.to_datetime(df[ts_col], errors="coerce").dt.date

    # User daily velocity
    g = df.groupby([user_col, "_date"], dropna=False)
    user_day = g[amt_col].agg(user_txn_amount_day="sum").reset_index()
    user_day["user_txn_count_day"] = g.size().values

    # Device change count per user per day (if device column exists)
    if device_col:
        # sort for successive comparison
        df_sorted = df.sort_values([user_col, ts_col]).copy()
        # change flag only when user stays same and device differs from previous
        prev_device = df_sorted.groupby(user_col)[device_col].shift(1)
        df_sorted["_device_changed"] = (df_sorted[device_col] != prev_device) & df_sorted[user_col].eq(
            df_sorted[user_col].shift(1)
        )
        # daily sum
        dev_daily = (
            df_sorted.groupby([user_col, df_sorted[ts_col].dt.date], dropna=False)["_device_changed"]
            .sum(min_count=1)
            .rename("device_change_count_day")
            .reset_index()
            .rename(columns={ts_col: "_date"})
        )
        user_day = user_day.merge(dev_daily, on=[user_col, "_date"], how="left")
    else:
        user_day["device_change_count_day"] = np.nan

    # Merchant chargeback rate (overall, placeholder)
    if merchant_col:
        m = df.groupby(merchant_col, dropna=False)
        txn_count = m.size().rename("txn_count")
        if cb_flag_col:
            chargeback_count = m[cb_flag_col].sum(min_count=1).rename("chargeback_count")
        else:
            chargeback_count = pd.Series(0, index=txn_count.index, name="chargeback_count")
        merchant_rates = (
            pd.concat([txn_count, chargeback_count], axis=1)
            .reset_index()
            .astype({ "txn_count": "Int64", "chargeback_count": "Int64" })
        )
        merchant_rates["merchant_chargeback_rate"] = (
            merchant_rates["chargeback_count"] / merchant_rates["txn_count"]
        )
    else:
        merchant_rates = pd.DataFrame(columns=["merchant_id", "txn_count", "chargeback_count", "merchant_chargeback_rate"])

    # Tidy
    user_day = user_day.rename(columns={"_date": "date"})
    return user_day, merchant_rates


def compute_stream_features(
    df: pd.DataFrame,
    user_col: str,
    ts_col: str,
    amt_col: str,
    country_col: Optional[str],
    tx_id_col: Optional[str],
    rolling_window: str = "1h",
) -> pd.DataFrame:
    """
    Per-transaction streaming-style features:
      - rolling_amount_last_1h (per user, time-based window)
      - geo_location_mismatch (current country != user's prior modal country)
    """
    # Ensure sorted for time-based rolling
    df = df.sort_values([user_col, ts_col]).copy()

    # Time-based rolling window per user using DataFrameGroupBy.rolling(on=...)
    rolled = (
        df.groupby(user_col)
          .rolling(rolling_window, on=ts_col)[amt_col]
          .sum()
          .reset_index(level=0, drop=True)  # drops the group key; keeps original row index
    )
    df["rolling_amount_last_1h"] = rolled

    # Geo mismatch: compare to prior modal country (computed up to previous row)
    if country_col:
        def _prior_mode_flags(s: pd.Series) -> pd.Series:
            counts = {}
            out = []
            for v in s:
                prior_mode = max(counts, key=counts.get) if counts else None
                out.append(False if prior_mode is None else (v != prior_mode))
                counts[v] = counts.get(v, 0) + 1
            return pd.Series(out, index=s.index)

        df["geo_location_mismatch"] = (
            df.groupby(user_col, group_keys=False)[country_col].apply(_prior_mode_flags)
        )
    else:
        df["geo_location_mismatch"] = np.nan

    keep = [c for c in [tx_id_col, user_col, ts_col, "rolling_amount_last_1h", "geo_location_mismatch"] if c]
    return df[keep].copy()


    # Rolling amount last 1h per user
    # Use time-based rolling window; requires DateTimeIndex per group
    def _rolling_amount(group: pd.DataFrame) -> pd.Series:
        g = group.set_index(ts_col)
        return g[amt_col].rolling(rolling_window, closed="both").sum().reset_index(drop=True)

    df["rolling_amount_last_1h"] = df.groupby(user_col, group_keys=False).apply(_rolling_amount)

    # Geo mismatch: current country != prior modal country (up to previous tx)
    if country_col:
        def _geo_mismatch(group: pd.DataFrame) -> pd.Series:
            counts = {}  # country -> count so far (before current row)
            out = []
            for _, row in group.iterrows():
                # prior mode (None for first)
                if counts:
                    prior_mode = max(counts, key=counts.get)
                else:
                    prior_mode = None
                out.append(False if prior_mode is None else (row[country_col] != prior_mode))
                # update counts after evaluating current row
                key = row[country_col]
                counts[key] = counts.get(key, 0) + 1
            return pd.Series(out, index=group.index)

        df["geo_location_mismatch"] = df.groupby(user_col, group_keys=False).apply(_geo_mismatch)
    else:
        df["geo_location_mismatch"] = np.nan

    # Keep compact columns for stream sink
    keep = [c for c in [tx_id_col, user_col, ts_col, "rolling_amount_last_1h", "geo_location_mismatch"] if c]
    return df[keep].copy()


# ---------- CLI ----------
SAMPLE_CSV = """transaction_id,user_id,merchant_id,device_id,amount,timestamp,is_chargeback,country
T1,U1,M1,D_A,120.50,2025-09-25T09:00:00,0,US
T2,U1,M1,D_A,80.00,2025-09-25T09:15:00,0,US
T3,U2,M2,D_X,15.75,2025-09-25T09:40:00,1,GB
T4,U1,M3,D_B,500.00,2025-09-25T10:05:00,0,CA
T5,U2,M2,D_X,40.25,2025-09-25T10:20:00,0,GB
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build fraud detection features (batch + streaming placeholders).")
    parser.add_argument(
        "--input",
        type=str,
        default="fraud_detection_system/data/raw/transactions.csv",
        help="Path to raw transactions CSV",
    )
    parser.add_argument(
        "--batch-out",
        type=str,
        default="fraud_detection_system/data/features_batch",
        help="Folder for batch features",
    )
    parser.add_argument(
        "--stream-out",
        type=str,
        default="fraud_detection_system/data/features_stream",
        help="Folder for streaming features",
    )
    parser.add_argument(
        "--window",
        type=str,
        default="1h",
        help="Rolling window for streaming amount (e.g. '30min', '1h', '2h')",
    )
    parser.add_argument(
        "--bootstrap-sample",
        action="store_true",
        help="If input is missing/empty, write a tiny sample CSV and continue.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    input_path = Path(args.input)
    batch_dir = Path(args.batch_out)
    stream_dir = Path(args.stream_out)
    batch_dir.mkdir(parents=True, exist_ok=True)
    stream_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Reading raw transactions: %s", input_path)
    if not input_path.exists() or (input_path.exists() and input_path.stat().st_size == 0):
        if args.bootstrap_sample:
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(SAMPLE_CSV, encoding="utf-8")
            logging.warning("Input missing/empty — wrote sample to: %s", input_path)
        else:
            logging.error("Input missing or empty: %s", input_path)
            logging.info("Tip: create it or rerun with --bootstrap-sample")
            return 2

    # Read and infer columns
    df = pd.read_csv(input_path)
    if df.shape[0] == 0 or df.shape[1] == 0:
        logging.error("Input has no rows/columns after read: %s", input_path)
        return 2

    # Pick columns with safe fallbacks
    user_col = pick_col(df, ["user_id", "customer_id", "account_id", "uid"], required=True)
    ts_col = pick_col(df, ["timestamp", "event_time", "trx_time", "transaction_time", "tx_time", "datetime"], required=True)
    amt_col = pick_col(df, ["amount", "transaction_amount", "amt", "value"], required=True)
    merchant_col = pick_col(df, ["merchant_id", "m_id", "store_id"], required=False)
    device_col = pick_col(df, ["device_id", "device", "device_hash", "device_fingerprint"], required=False)
    cb_flag_col = pick_col(df, ["is_chargeback", "chargeback", "cbk_flag", "is_fraud_chargeback"], required=False)
    country_col = pick_col(df, ["country", "country_code", "geo_country", "location_country", "country_iso"], required=False)
    tx_id_col = pick_col(df, ["transaction_id", "tx_id", "id"], required=False)

    # Coerce types
    df[ts_col] = ensure_datetime(df[ts_col])
    df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce")
    if cb_flag_col:
        # Support 0/1 or 'Y'/'N' or True/False
        if df[cb_flag_col].dtype == object:
            df[cb_flag_col] = df[cb_flag_col].astype(str).str.strip().str.upper().map({"1": 1, "0": 0, "Y": 1, "N": 0, "TRUE": 1, "FALSE": 0})
        df[cb_flag_col] = pd.to_numeric(df[cb_flag_col], errors="coerce").fillna(0).astype(int)

    # -------- batch features --------
    logging.info("Computing batch features (user velocity, device changes, merchant chargeback rate)…")
    user_day, merchant_rates = compute_batch_features(df, user_col, ts_col, amt_col, device_col, merchant_col, cb_flag_col)

    # Write batch outputs
    user_day_path = batch_dir / "user_daily_velocity.parquet"
    dev_change_path = batch_dir / "device_change_count_daily.parquet"  # merged in user_day; kept for clarity (same file)
    merchant_path = batch_dir / "merchant_chargeback_rate.parquet"

    try:
        user_day.to_parquet(user_day_path, index=False)
        # device changes already inside user_day; duplicate write for discoverability
        user_day.to_parquet(dev_change_path, index=False)
        if not merchant_rates.empty:
            merchant_rates.to_parquet(merchant_path, index=False)
        logging.info("Wrote batch features (Parquet).")
    except Exception as e:
        logging.warning("Parquet write failed (%s). Writing CSV fallbacks.", repr(e))
        user_day.to_csv(user_day_path.with_suffix(".csv"), index=False)
        user_day.to_csv(dev_change_path.with_suffix(".csv"), index=False)
        if not merchant_rates.empty:
            merchant_rates.to_csv(merchant_path.with_suffix(".csv"), index=False)
        logging.info("CSV fallbacks written. Tip: install pyarrow for Parquet.")

    # -------- streaming features --------
    logging.info("Computing streaming features (rolling_amount_last_%s, geo_location_mismatch)…", args.window)
    stream_df = compute_stream_features(df, user_col, ts_col, amt_col, country_col, tx_id_col, rolling_window=args.window)

    stream_path = stream_dir / "stream_features.parquet"
    try:
        stream_df.to_parquet(stream_path, index=False)
        logging.info("Wrote streaming features (Parquet).")
    except Exception as e:
        logging.warning("Parquet write failed (%s). Writing CSV fallback.", repr(e))
        stream_df.to_csv(stream_path.with_suffix(".csv"), index=False)
        logging.info("CSV fallback written. Tip: install pyarrow for Parquet.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
