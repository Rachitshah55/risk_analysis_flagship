#!/usr/bin/env python
from __future__ import annotations

import argparse
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd


def pick_col(df: pd.DataFrame, candidates: list[str], required: bool = False) -> str | None:
    """
    Return the first column from `candidates` that exists in df.columns.
    If `required` and none found, raise KeyError.
    """
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"Required column not found. Tried: {candidates}")
    warnings.warn(f"None of the columns found: {candidates}")
    return None


def coerce_percent(x) -> float | np.float64 | None:
    if pd.isna(x):
        return np.nan
    if isinstance(x, str):
        s = x.strip().replace("%", "")
        try:
            return float(s)
        except ValueError:
            return np.nan
    try:
        return float(x)
    except Exception:
        return np.nan


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute borrower-level features with safe fallbacks for common schema variants.
    Outputs columns:
        - <entity_id> (borrower identifier chosen from common names)
        - income_to_loan_ratio
        - num_past_delinquencies
        - credit_utilization_pct
        - n_records  (rows contributing to the aggregate)
    """
    # Choose an entity id
    id_col = pick_col(
        df,
        ["borrower_id", "member_id", "customer_id", "client_id", "uid", "applicant_id", "loan_id"],
        required=False,
    )
    if not id_col:
        df = df.reset_index(drop=False).rename(columns={"index": "entity_id"})
        id_col = "entity_id"

    # Required core columns (try several common names)
    loan_col = pick_col(df, ["loan_amount", "loan_amnt", "funded_amnt", "principal", "amount"], required=True)
    inc_col = pick_col(df, ["annual_income", "annual_inc", "income", "applicant_income"], required=True)

    # Optional delinquencies column
    delq_col = pick_col(
        df, ["num_past_delinquencies", "delinq_2yrs", "total_late_payments", "late_payments", "past_delinquencies"]
    )

    # Feature: income_to_loan_ratio
    loan_amt = pd.to_numeric(df[loan_col], errors="coerce")
    income = pd.to_numeric(df[inc_col], errors="coerce")
    ratio = income / loan_amt
    ratio.replace([np.inf, -np.inf], np.nan, inplace=True)
    df["_income_to_loan_ratio"] = ratio

    # Feature: num_past_delinquencies
    if delq_col:
        df["_num_past_delinquencies"] = pd.to_numeric(df[delq_col], errors="coerce")
    else:
        df["_num_past_delinquencies"] = np.nan

    # Feature: credit_utilization_pct
    if "revol_util" in df.columns:
        df["_credit_utilization_pct"] = df["revol_util"].map(coerce_percent)
    else:
        bal_col = pick_col(df, ["revol_bal", "current_credit_balance", "total_balance"])
        lim_col = pick_col(df, ["total_rev_hi_lim", "total_credit_limit", "credit_limit"])
        if bal_col and lim_col:
            bal = pd.to_numeric(df[bal_col], errors="coerce")
            lim = pd.to_numeric(df[lim_col], errors="coerce")
            util = (bal / lim) * 100.0
            util.replace([np.inf, -np.inf], np.nan, inplace=True)
            df["_credit_utilization_pct"] = util
        else:
            df["_credit_utilization_pct"] = np.nan

    # Aggregate to borrower-level if multiple rows per id
    grouped = df.groupby(id_col, dropna=False)
    out = grouped["_income_to_loan_ratio"].mean().to_frame("income_to_loan_ratio")
    out["num_past_delinquencies"] = grouped["_num_past_delinquencies"].max()
    out["credit_utilization_pct"] = grouped["_credit_utilization_pct"].mean()
    out["n_records"] = grouped.size().values
    out = out.reset_index()

    # Ensure clean numeric types
    for c in ["income_to_loan_ratio", "num_past_delinquencies", "credit_utilization_pct"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build borrower-level credit features (placeholder pipeline).")
    parser.add_argument(
        "--input",
        type=str,
        default="credit_scoring_system/data/raw/loans.csv",
        help="Path to raw loans CSV (default: credit_scoring_system/data/raw/loans.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="credit_scoring_system/data/featurestore/credit_features.parquet",
        help="Path to write features Parquet (default: credit_scoring_system/data/featurestore/credit_features.parquet)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logging.info("Reading raw CSV: %s", input_path)
    df = pd.read_csv(input_path)

    logging.info("Computing features…")
    feats = compute_features(df)

    logging.info("Writing features: %s", output_path)
    try:
        feats.to_parquet(output_path, index=False)
        logging.info("Wrote Parquet OK.")
    except Exception as e:
        logging.warning("Parquet write failed (%s). Writing CSV fallback.", repr(e))
        alt = output_path.with_suffix(".csv")
        feats.to_csv(alt, index=False)
        logging.info("Wrote CSV fallback: %s", alt)
        logging.info("Tip: install Parquet support with:  .venv\\Scripts\\python.exe -m pip install pyarrow")

    return 0


if __name__ == "__main__":
    sys.exit(main())