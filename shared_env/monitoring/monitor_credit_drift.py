# ===== BEGIN: monitor_credit_drift.py =====
import os, sys, json, math, argparse, re
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# --- Evidently HTML report builder (0.7+ Dataset + DataDefinition) with guards & fallback ---
def build_evidently_report(ref_df, cur_df, cols, out_html):
    """
    Evidently 0.7+ flow with safety guards:
      • Keep mutual columns only; restrict to numeric features
      • Drop columns that are constant or too sparse (prevents NumPy warnings)
      • Try DataDriftPreset(method="psi", columns=[...]); fallback to ValueDrift per column
      • On success, remove any stale evidently_error.txt
      • If columns were dropped, write dropped_columns.csv next to the HTML
    Returns True on Evidently HTML success; False (caller will write simple fallback HTML).
    """
    from pathlib import Path
    import warnings

    err_path = Path(out_html).with_name("evidently_error.txt")
    try:
        if err_path.exists():
            err_path.unlink()
    except Exception:
        pass

    def note(tag, exc):
        try:
            with err_path.open("a", encoding="utf-8") as f:
                f.write(f"[{tag} failed] {exc}\n")
        except Exception:
            pass

    # 1) Keep only mutual columns, then restrict to numeric features
    cols = [c for c in cols if c in ref_df.columns and c in cur_df.columns]
    numeric_cols = [c for c in cols
                    if pd.api.types.is_numeric_dtype(ref_df[c]) or pd.api.types.is_numeric_dtype(cur_df[c])]
    if not numeric_cols:
        note("prepare", "No numeric columns available for drift; skipping Evidently.")
        return False

    ref_num_df = ref_df[numeric_cols].copy()
    cur_num_df = cur_df[numeric_cols].copy()

    # 2) Stability guard: drop constant / too-sparse columns (avoid NumPy divide warnings)
    combined = pd.concat([ref_num_df, cur_num_df], ignore_index=True)
    keep_cols, dropped = [], []
    MIN_NONNULL = 3
    for c in numeric_cols:
        nn_ref = int(ref_num_df[c].notna().sum())
        nn_cur = int(cur_num_df[c].notna().sum())
        std_all = float(pd.to_numeric(combined[c], errors="coerce").std(skipna=True) or 0.0)
        if nn_ref >= MIN_NONNULL and nn_cur >= MIN_NONNULL and std_all > 0.0:
            keep_cols.append(c)
        else:
            dropped.append({"feature": c, "nn_ref": nn_ref, "nn_cur": nn_cur, "std_all": std_all})

    if dropped:
        try:
            pd.DataFrame(dropped).to_csv(Path(out_html).with_name("dropped_columns.csv"), index=False)
        except Exception:
            pass

    if not keep_cols:
        note("prepare", "All numeric columns were constant or too sparse; skipping Evidently.")
        return False

    ref_num_df = ref_num_df[keep_cols]
    cur_num_df = cur_num_df[keep_cols]

    # 3) Preferred path: 0.7+ Dataset + DataDefinition + DataDriftPreset (columns=..., method='psi')
    try:
        from evidently import Report, Dataset, DataDefinition
        from evidently.presets import DataDriftPreset

        definition = DataDefinition(numerical_columns=keep_cols)
        ref_ds = Dataset.from_pandas(ref_num_df, data_definition=definition)
        cur_ds = Dataset.from_pandas(cur_num_df, data_definition=definition)

        report = Report([DataDriftPreset(method="psi", columns=keep_cols)])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",
                                    message="invalid value encountered in divide",
                                    category=RuntimeWarning,
                                    module="numpy")
            snapshot = report.run(cur_ds, ref_ds)  # (current, reference)
            snapshot.save_html(out_html)

        if err_path.exists():
            err_path.unlink(missing_ok=True)
        return True
    except Exception as e_preset:
        note("0.7(preset)", e_preset)

    # 4) Fallback: 0.7+ Dataset + per-column ValueDrift(method='psi')
    try:
        from evidently import Report, Dataset, DataDefinition
        from evidently.metrics import ValueDrift

        definition = DataDefinition(numerical_columns=keep_cols)
        ref_ds = Dataset.from_pandas(ref_num_df, data_definition=definition)
        cur_ds = Dataset.from_pandas(cur_num_df, data_definition=definition)

        metrics = [ValueDrift(column=c, method="psi") for c in keep_cols]
        report = Report(metrics)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore",
                                    message="invalid value encountered in divide",
                                    category=RuntimeWarning,
                                    module="numpy")
            snapshot = report.run(cur_ds, ref_ds)
            snapshot.save_html(out_html)

        if err_path.exists():
            err_path.unlink(missing_ok=True)  # clear earlier errors since we succeeded
        return True
    except Exception as e_val:
        note("0.7(ValueDrift)", e_val)
        print(f"[WARN] Evidently HTML report skipped (see {err_path.name}).")
        return False




# --- PSI helpers ---
def psi_for_col(ref, cur, buckets=10, eps=1e-6):
    ref = pd.Series(ref).dropna().astype(float)
    cur = pd.Series(cur).dropna().astype(float)
    if ref.empty or cur.empty:
        return np.nan
    qs = np.linspace(0, 1, buckets + 1)
    try:
        edges = np.unique(np.quantile(ref, qs))
        if len(edges) < 2:
            return np.nan
        ref_counts, _ = np.histogram(ref, bins=edges)
        cur_counts, _ = np.histogram(cur, bins=edges)
    except Exception:
        edges = np.linspace(ref.min(), ref.max(), buckets + 1)
        ref_counts, _ = np.histogram(ref, bins=edges)
        cur_counts, _ = np.histogram(cur, bins=edges)
    ref_pct = (ref_counts + eps) / (ref_counts.sum() + eps * len(ref_counts))
    cur_pct = (cur_counts + eps) / (cur_counts.sum() + eps * len(cur_counts))
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def compute_psi_table(ref_df, cur_df, cols):
    rows = []
    for c in cols:
        try:
            v = psi_for_col(ref_df[c], cur_df[c])
        except Exception:
            v = np.nan
        rows.append({"feature": c, "psi": v})
    out = pd.DataFrame(rows).sort_values("psi", ascending=False)
    return out


# --- File helpers ---
def parse_score_date_from_name(p: Path):
    m = re.search(r"pd_scores_(\d{8})\.parquet$", p.name)
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y%m%d")


def latest_two_scoring_files(out_dir: Path):
    files = sorted(out_dir.glob("pd_scores_*.parquet"), key=lambda p: p.name)
    if len(files) < 2:
        raise FileNotFoundError("Need at least two monthly PD score files.")
    return files[-2], files[-1]


# --- Data helpers ---
def normalize_pd_column(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a lowercase 'pd' column exists (alias common variants)."""
    if "pd" in df.columns:
        return df
    for cand in ["PD", "Pd", "pd_score", "prob_default", "score_pd", "prob_of_default"]:
        if cand in df.columns:
            df = df.copy()
            df["pd"] = df[cand]
            return df
    return df


def try_load_labels(loans_path: Path):
    if not loans_path.exists():
        return None
    df = pd.read_csv(loans_path)
    for cand in ["defaulted", "loan_status", "is_default", "target"]:
        if cand in df.columns:
            y = df[["borrower_id", cand]].copy() if "borrower_id" in df.columns else None
            return (cand, y)
    return None


def make_calibration_plot(cur_scores: pd.DataFrame, label_info, out_png: Path):
    # Requires borrower_id, pd columns in scores; label_info is (label_col, df) or None
    if label_info is None:
        with open(out_png.with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write("Calibration skipped: labels not available.\n")
        return False

    label_col, labels_df = label_info
    if "borrower_id" not in cur_scores.columns or labels_df is None or "borrower_id" not in labels_df.columns:
        with open(out_png.with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write("Calibration skipped: borrower_id not found for merge.\n")
        return False

    df = cur_scores.merge(labels_df, on="borrower_id", how="inner")

    if "pd" not in df.columns:
        for c in ["PD", "Pd", "pd_score", "prob_default", "score_pd", "prob_of_default"]:
            if c in df.columns:
                df["pd"] = df[c]
                break
    if "pd" not in df.columns:
        with open(out_png.with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write("Calibration skipped: 'pd' column not found.\n")
        return False

    df = df[["pd", label_col]].dropna()
    if df.empty:
        return False

    df["bin"] = pd.qcut(df["pd"], q=10, duplicates="drop")
    cal = df.groupby("bin", observed=False).agg(
        mean_pd=("pd", "mean"),
        rate_observed=(
            label_col,
            lambda s: float(
                np.mean(
                    pd.Series(s).astype(str).str.lower().isin(
                        ["1", "true", "yes", "default", "bad", "charged_off", "writeoff"]
                    )
                    | (pd.to_numeric(pd.Series(s), errors="coerce") == 1)
                )
            ),
        ),
    ).reset_index(drop=True)

    plt.figure(figsize=(6, 4))
    plt.plot(cal["mean_pd"], cal["rate_observed"], marker="o")
    plt.xlabel("Predicted PD (bin average)")
    plt.ylabel("Observed default rate")
    plt.title("Calibration (by PD decile)")
    plt.grid(True, alpha=0.3)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="CI smoke test mode (uses tiny synthetic data).")
    args = ap.parse_args()

    root = Path(r"C:\DevProjects\risk_analysis_flagship")
    scores_dir = root / r"credit_scoring_system\outputs\scoring"

    if args.dry_run:
        ref = pd.DataFrame({"pd": [0.01, 0.02, 0.03], "income_to_loan_ratio": [2, 3, 4]})
        cur = pd.DataFrame({"pd": [0.02, 0.03, 0.05], "income_to_loan_ratio": [2.2, 3.1, 3.8]})
        cur_dt = datetime.now()
    else:
        ref_path, cur_path = latest_two_scoring_files(scores_dir)
        ref = pd.read_parquet(ref_path)
        cur = pd.read_parquet(cur_path)
        cur_dt = parse_score_date_from_name(cur_path) or datetime.now()

    # Normalize PD column so it's always present when possible
    ref = normalize_pd_column(ref)
    cur = normalize_pd_column(cur)

    out_month_dir = root / f"docs_global/monitoring/credit/{cur_dt.strftime('%Y-%m')}"
    out_month_dir.mkdir(parents=True, exist_ok=True)

    # Feature set to drift-check (numeric only, plus pd if present)
    numeric_candidates = [c for c in ref.columns if pd.api.types.is_numeric_dtype(ref[c]) and c != "borrower_id"]
    monitor_cols = ["pd"] + [c for c in numeric_candidates if c != "pd"][:24]  # ensure 'pd' first; cap for safety

    # Evidently HTML (best-effort, with fallback)
    drift_html = out_month_dir / "drift_report.html"
    ok_html = build_evidently_report(ref, cur, monitor_cols, drift_html.as_posix())

    # PSI table (incl. pd)
    psi_df = compute_psi_table(ref, cur, monitor_cols)
    psi_csv = out_month_dir / "drift_summary.csv"
    psi_df.to_csv(psi_csv, index=False)

    # Minimal HTML fallback if Evidently failed to create the file
    if not ok_html or not drift_html.exists():
        psi_df.to_html(drift_html, index=False)

    # Alert if any PSI >= 0.25
    alert_path = out_month_dir / "alert.txt"
    hit = psi_df["psi"].fillna(0).ge(0.25).any()
    if hit:
        bad = psi_df.sort_values("psi", ascending=False).head(5)
        with open(alert_path, "w", encoding="utf-8") as f:
            f.write("DRIFT ALERT (PSI >= 0.25)\n\nTop offenders:\n")
            f.write(bad.to_string(index=False))
    else:
        if alert_path.exists():
            try:
                alert_path.unlink()
            except Exception:
                pass

    # Calibration (optional if labels exist)
    cal_png = out_month_dir / "calibration_plot.png"
    label_info = try_load_labels(root / r"credit_scoring_system\data\raw\loans.csv")
    make_calibration_plot(cur, label_info, cal_png)

    # MLflow logging (best-effort)
    try:
        import mlflow
        mlflow.set_experiment("credit_stage5_monitoring")
        with mlflow.start_run(run_name=f"credit_monitor_{datetime.now():%Y%m%d_%H%M%S}"):
            mlflow.log_metric("max_psi", float(psi_df["psi"].max()))
            pd_psi = float(psi_df.loc[psi_df["feature"] == "pd", "psi"].values[0]) if "pd" in psi_df["feature"].values else float("nan")
            mlflow.log_metric("pd_psi", pd_psi)
            mlflow.log_artifact(psi_csv.as_posix())
            if drift_html.exists():
                mlflow.log_artifact(drift_html.as_posix())
            if cal_png.exists():
                mlflow.log_artifact(cal_png.as_posix())
            if alert_path.exists():
                mlflow.log_artifact(alert_path.as_posix())
    except Exception as e:
        print(f"[WARN] MLflow logging skipped: {e}")

    print(f"[OK] Credit monitoring written to: {out_month_dir}")


if __name__ == "__main__":
    main()
# ===== END: monitor_credit_drift.py =====
