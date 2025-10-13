from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FRAUD = ROOT / "fraud_detection_system"

CFG = FRAUD / "config" / "fraud_labels_config.json"
TRAIN_LABELED = FRAUD / "data" / "training" / "transactions_labeled.csv"
RAW_NO_LABEL = FRAUD / "data" / "raw" / "transactions.csv"
LABELS_DIR = FRAUD / "data" / "labels"

def read_cfg_label():
    if CFG.exists():
        try:
            cfg = json.load(open(CFG, "r", encoding="utf-8"))
            lab = cfg.get("label_column")
            if isinstance(lab, str) and lab.strip():
                return lab.strip()
        except Exception:
            pass
    return None

def main():
    label = read_cfg_label()
    print(f"[CFG] label_column = {label!r}")
    if TRAIN_LABELED.exists():
        df = pd.read_csv(TRAIN_LABELED)
        print(f"[DATA] training_labeled exists: {TRAIN_LABELED}")
        print(f"[DATA] shape: {df.shape}, columns: {list(df.columns)[:12]}")
        found = label in df.columns if label else False
        if not found:
            for c in ["is_fraud","is_chargeback","label","fraud_flag","chargeback"]:
                if c in df.columns:
                    label = label or c
                    found = True
                    break
        print(f"[DATA] resolved label_column in training_labeled = {label!r}, present={found}")
        if found:
            print("[OK] You can train directly from training_labeled.csv")
            return
        else:
            print("[WARN] Label column not present in training_labeled.csv")

    if RAW_NO_LABEL.exists():
        base = pd.read_csv(RAW_NO_LABEL)
        print(f"[DATA] raw exists: {RAW_NO_LABEL}, shape: {base.shape}")
        if "txn_id" not in base.columns:
            print("[ERR] raw lacks 'txn_id'. Cannot join labels. Either add a labeled training file or add txn_id to raw+labels.")
            return
        lbl_files = sorted(LABELS_DIR.glob("transactions_labels_*.csv"))
        if not lbl_files:
            print(f"[ERR] no labels found in {LABELS_DIR}. Add transactions_labels_YYYY-MM.csv with txn_id and your label.")
            return
        lbl = pd.read_csv(lbl_files[-1])
        print(f"[DATA] newest labels: {lbl_files[-1]}, shape: {lbl.shape}, columns: {list(lbl.columns)[:12]}")
        if "txn_id" not in lbl.columns:
            print("[ERR] labels file has no txn_id. Cannot join.")
            return
        if label is None:
            for c in ["is_fraud","is_chargeback","label","fraud_flag","chargeback"]:
                if c in lbl.columns:
                    label = c
                    break
        if label is None or label not in lbl.columns:
            print(f"[ERR] could not resolve label column. Set it in {CFG} or add one of common names to labels file.")
            return
        merged = base.merge(lbl, on="txn_id", how="inner")
        print(f"[OK] raw+labels join works. merged shape: {merged.shape}, label_column: {label!r}")
        return

    print("[ERR] no usable dataset found. Ensure either training_labeled.csv exists with a label column, or raw+labels join is possible.")

if __name__ == "__main__":
    main()
