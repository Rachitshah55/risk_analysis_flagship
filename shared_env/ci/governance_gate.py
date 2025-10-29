# shared_env/ci/governance_gate.py
# Purpose: Fail CI when governance rules are violated.
# - If fraud rules (*.yml) changed -> CHANGELOG must be updated in the same change.
# - If models changed -> corresponding model card(s) must be updated in the same change.
# - On release branches or tags -> an audit pack folder must exist under docs_global/audits/.
#
# Works for both push and pull_request using the SHAs provided by the workflow env.
# Uses only stdlib. Prints clear messages and exits 1 on failure.

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

def sh(cmd: List[str]) -> Tuple[int, str]:
    p = subprocess.Popen(cmd, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate()
    return p.returncode, out

def get_changed_files() -> List[str]:
    head = os.getenv("HEAD_SHA", "").strip()
    pr_base = os.getenv("PR_BASE_SHA", "").strip()
    push_base = os.getenv("PUSH_BASE_SHA", "").strip()

    base = ""
    # prefer PR base when present (pull_request), else push base, else fallback to HEAD^
    if pr_base:
        base = pr_base
    elif push_base:
        base = push_base
    else:
        # fallback for odd cases — previous commit
        rc, out = sh(["git", "rev-parse", "HEAD^"])
        if rc != 0:
            print("[WARN] Could not find HEAD^; using 'git show --name-only'")
            rc2, out2 = sh(["git", "show", "--name-only", "--pretty="])
            return [line.strip() for line in out2.splitlines() if line.strip()]
        base = out.strip()

    # Ensure we have the base commit locally
    sh(["git", "fetch", "--no-tags", "--prune", "--depth=2", "origin", base])

    rc, out = sh(["git", "diff", "--name-only", f"{base}", f"{head or 'HEAD'}"])
    if rc != 0:
        print(out)
        print("[ERROR] Failed to diff changes.")
        sys.exit(1)
    files = [line.strip() for line in out.splitlines() if line.strip()]
    print(f"[INFO] Changed files count: {len(files)}")
    for f in files:
        print(f" - {f}")
    return files

def fail(msg: str) -> None:
    print(f"\n[FAIL] {msg}\n")
    sys.exit(1)

def main() -> None:
    changed = get_changed_files()

    rules_dir = os.getenv("RULES_DIR", "fraud_detection_system/rules").rstrip("/\\")
    rules_changelog = os.getenv("RULES_CHANGELOG", f"{rules_dir}/CHANGELOG.md").replace("\\", "/")
    credit_models_dir = os.getenv("CREDIT_MODELS_DIR", "credit_scoring_system/models").rstrip("/\\")
    fraud_models_dir  = os.getenv("FRAUD_MODELS_DIR", "fraud_detection_system/models").rstrip("/\\")
    credit_card = os.getenv("CREDIT_CARD", "docs/model_cards/credit_model.md").replace("\\", "/")
    fraud_card  = os.getenv("FRAUD_CARD", "docs/model_cards/fraud_model.md").replace("\\", "/")
    audits_dir  = os.getenv("AUDITS_DIR", "docs_global/audits").rstrip("/\\")
    ref_name    = os.getenv("GITHUB_REF_NAME", "")
    ref_full    = os.getenv("GITHUB_REF", "")

    # ---- Rule 1: rules change requires CHANGELOG bump
    rules_changed = any(f.startswith(f"{rules_dir}/") and f.endswith(".yml") for f in changed)
    if rules_changed:
        if rules_changelog not in changed:
            fail(f"Fraud rules changed, but {rules_changelog} not updated in the same change.")
        else:
            # Minimal semantic check: last 50 lines of changelog must contain a "## " section header
            path = REPO_ROOT / rules_changelog
            if not path.exists():
                fail(f"{rules_changelog} not found after being listed as changed.")
            last = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-50:]
            if not any(line.strip().startswith("## ") for line in last):
                fail(f"{rules_changelog} must include a new version header like '## vX.Y.Z - YYYY-MM-DD'.")

    # ---- Rule 2: model changes require model card updates
    credit_models_touched = any(f.startswith(f"{credit_models_dir}/") for f in changed)
    fraud_models_touched  = any(f.startswith(f"{fraud_models_dir}/")  for f in changed)
    if credit_models_touched and (credit_card not in changed):
        fail(f"Credit models changed, but {credit_card} not updated in the same change.")
    if fraud_models_touched and (fraud_card not in changed):
        fail(f"Fraud models changed, but {fraud_card} not updated in the same change.")

    # ---- Rule 3: audit pack required on release branches/tags
    # Consider 'release/*' branches or tags 'v*' as release lines.
    is_release_line = (ref_full.startswith("refs/heads/release/") or ref_full.startswith("refs/tags/v"))
    if is_release_line:
        audits_path = REPO_ROOT / audits_dir
        if not audits_path.exists() or not any(p.is_dir() for p in audits_path.glob("*")):
            fail(f"Release detected ({ref_name}). Expected a dated audit folder under {audits_dir}/.")

    print("\n[OK] Governance checks passed.\n")

if __name__ == "__main__":
    main()
