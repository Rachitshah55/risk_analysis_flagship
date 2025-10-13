# C:\DevProjects\risk_analysis_flagship\shared_env\monitoring\run_credit_daily_full.py
import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")

S5 = ROOT / "shared_env" / "monitoring" / "monitor_credit_drift.py"
S6 = ROOT / "credit_scoring_system" / "reports" / "run_daily_credit_report.py"

S4_CANDIDATES = [
    ROOT / "credit_scoring_system" / "scripts" / "score_credit_portfolio.py",  # <-- added
    ROOT / "credit_scoring_system" / "scripts" / "score_portfolio.py",
    ROOT / "credit_scoring_system" / "scripts" / "run_batch_scoring.py",
    ROOT / "credit_scoring_system" / "scripts" / "batch_score_portfolio.py",
]

def find_stage4():
    # allow explicit override via env var
    override = os.environ.get("STAGE4_PATH")
    if override:
        p = Path(override)
        if p.exists():
            return p
    for p in S4_CANDIDATES:
        if p.exists():
            return p
    return None

def run(cmd):
    print("[RUN]", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)

def main():
    # Stage 5
    if not S5.exists():
        raise FileNotFoundError(f"Stage 5 monitor not found: {S5}")
    print("[Chain] Stage 5: Credit monitor...")
    run([PY, str(S5)])

    # Stage 4
    s4 = find_stage4()
    if s4:
        print(f"[Chain] Stage 4: Batch scoring via {s4.name} ...")
        run([PY, str(s4)])
    else:
        print("[Chain] Stage 4: No scorer script found — skipping (PD/EL KPIs will be None).")

    # Stage 6
    if not S6.exists():
        raise FileNotFoundError(f"Stage 6 runner not found: {S6}")
    print("[Chain] Stage 6: Daily report...")
    run([PY, str(S6)])

    print("[Chain] DONE.")

if __name__ == "__main__":
    main()
