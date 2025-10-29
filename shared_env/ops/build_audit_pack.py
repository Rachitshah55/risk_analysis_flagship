# shared_env/ops/build_audit_pack.py
"""
Builds a dated audit pack under docs_global/audits/YYYY-MM-DD/{credit|fraud}/ with:
- Final model cards (credit & fraud)
- Last 14 days of monitoring (credit & fraud) if available
- Latest monthly summaries (credit & fraud)
- Fraud rules (CHANGELOG + rules_*.yml) with SHA256 hashes
- PROD_POINTER.txt for both systems (if present)
- A small approvals template and evidence.json manifest

Safe on Windows and Linux. Uses only stdlib.
"""

from __future__ import annotations
import hashlib
import json
import shutil
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
TODAY = date.today().isoformat()
DEST_ROOT = ROOT / "docs_global" / "audits" / TODAY

# Source paths (adjust if your layout differs)
CREDIT_CARD = ROOT / "docs" / "model_cards" / "credit_model.md"
FRAUD_CARD  = ROOT / "docs" / "model_cards" / "fraud_model.md"

CREDIT_MON_ROOT = ROOT / "docs_global" / "monitoring" / "credit"
FRAUD_MON_ROOT  = ROOT / "docs_global" / "monitoring" / "fraud"

CREDIT_REPORTS_ROOT = ROOT / "docs_global" / "reports" / "credit"
FRAUD_REPORTS_ROOT  = ROOT / "docs_global" / "reports" / "fraud"

CREDIT_PROD_PTR = ROOT / "credit_scoring_system" / "models" / "PROD_POINTER.txt"
FRAUD_PROD_PTR  = ROOT / "fraud_detection_system" / "models" / "PROD_POINTER.txt"

RULES_DIR = ROOT / "fraud_detection_system" / "rules"
RULES_CHANGELOG = RULES_DIR / "CHANGELOG.md"

@dataclass
class CopiedItem:
    src: str
    dst: str
    sha256: Optional[str] = None

@dataclass
class Evidence:
    date: str
    credit: Dict[str, List[CopiedItem]]
    fraud: Dict[str, List[CopiedItem]]
    notes: List[str]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_copy(src: Path, dst: Path, record: List[CopiedItem], hash_it: bool = False) -> None:
    if not src.exists():
        print(f"[WARN] Missing: {src}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        record.append(CopiedItem(str(src.relative_to(ROOT)), str(dst.relative_to(ROOT)), None))
    else:
        shutil.copy2(src, dst)
        record.append(CopiedItem(
            str(src.relative_to(ROOT)),
            str(dst.relative_to(ROOT)),
            sha256_file(src) if hash_it else None
        ))

def pick_latest_month_folder(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    candidates = [p for p in root.iterdir() if p.is_dir() and len(p.name) == 7 and "-" in p.name]
    if not candidates:
        return None
    return sorted(candidates)[-1]

def pick_last_n_daily_folders(root: Path, n: int = 14) -> List[Path]:
    if not root.exists():
        return []
    days = [p for p in root.iterdir() if p.is_dir() and len(p.name) == 10 and p.name.count("-") == 2]
    return sorted(days)[-n:]

def main() -> None:
    credit_log: Dict[str, List[CopiedItem]] = {"model_card": [], "monitoring": [], "monthly": [], "prod_pointer": []}
    fraud_log:  Dict[str, List[CopiedItem]] = {"model_card": [], "monitoring": [], "monthly": [], "rules": [], "prod_pointer": []}
    notes: List[str] = []

    credit_dst = DEST_ROOT / "credit"
    fraud_dst  = DEST_ROOT / "fraud"
    credit_dst.mkdir(parents=True, exist_ok=True)
    fraud_dst.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Building audit pack at: {DEST_ROOT}")

    # 1) Model cards
    safe_copy(CREDIT_CARD, credit_dst / "credit_model.md", credit_log["model_card"])
    safe_copy(FRAUD_CARD,  fraud_dst  / "fraud_model.md",  fraud_log["model_card"])

    # 2) Monitoring (last 14 days)
    for d in pick_last_n_daily_folders(CREDIT_MON_ROOT, n=14):
        safe_copy(d, credit_dst / "monitoring" / d.name, credit_log["monitoring"])
    for d in pick_last_n_daily_folders(FRAUD_MON_ROOT, n=14):
        safe_copy(d, fraud_dst / "monitoring" / d.name, fraud_log["monitoring"])

    # 3) Monthly roll-ups (latest YYYY-MM folder)
    c_month = pick_latest_month_folder(CREDIT_REPORTS_ROOT)
    if c_month:
        safe_copy(c_month, credit_dst / "monthly" / c_month.name, credit_log["monthly"])
    else:
        notes.append("Credit monthly folder not found; skipping.")

    f_month = pick_latest_month_folder(FRAUD_REPORTS_ROOT)
    if f_month:
        safe_copy(f_month, fraud_dst / "monthly" / f_month.name, fraud_log["monthly"])
    else:
        notes.append("Fraud monthly folder not found; skipping.")

    # 4) PROD pointers
    safe_copy(CREDIT_PROD_PTR, credit_dst / "PROD_POINTER.txt", credit_log["prod_pointer"], hash_it=True)
    safe_copy(FRAUD_PROD_PTR,  fraud_dst  / "PROD_POINTER.txt",  fraud_log["prod_pointer"],  hash_it=True)

    # 5) Rules changelog + rules files with hashes
    if RULES_DIR.exists():
        safe_copy(RULES_CHANGELOG, fraud_dst / "rules" / "CHANGELOG.md", fraud_log["rules"])
        for yml in RULES_DIR.glob("rules_*.yml"):
            safe_copy(yml, fraud_dst / "rules" / yml.name, fraud_log["rules"], hash_it=True)
    else:
        notes.append("Rules directory not found; skipping rules copy.")

    # 6) Approvals template (create if not present)
    approvals = DEST_ROOT / "APPROVALS_TEMPLATE.md"
    if not approvals.exists():
        approvals.write_text(
            "# Approvals — Stage 9 Audit Pack\n\n"
            "## Credit\n- Owner Review: __________________ (Date: ________)\n"
            "- Risk Lead Sign-off: ____________ (Date: ________)\n\n"
            "## Fraud\n- Owner Review: __________________ (Date: ________)\n"
            "- Risk Lead Sign-off: ____________ (Date: ________)\n\n"
            "## Release\n- Release Manager: _______________ (Date: ________)\n"
            "- Notes: ________________________________\n",
            encoding="utf-8"
        )

    # 7) Manifest (evidence.json) — FIX: serialize dataclasses with asdict()
    ev = Evidence(
        date=TODAY,
        credit=credit_log,
        fraud=fraud_log,
        notes=notes
    )
    (DEST_ROOT / "evidence.json").write_text(json.dumps(asdict(ev), indent=2), encoding="utf-8")

    print("[OK] Audit pack assembled.")
    print(f" - {DEST_ROOT}")

if __name__ == "__main__":
    main()
