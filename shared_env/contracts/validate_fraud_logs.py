from pathlib import Path
import sys, json

ROOT = Path(__file__).resolve().parents[2]

def open_last_jsonl():
    logs = ROOT / "fraud_detection_system" / "api" / "logs"
    days = sorted(logs.glob("*.jsonl"))
    return days[-1] if days else None

def main():
    f = open_last_jsonl()
    if not f:
        print("[WARN] No fraud JSONL logs found — skipping.")
        return 0
    # scan up to first 100 lines
    need = {"ts","decision","proba","latency_ms"}
    n=0
    with f.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            n+=1
            if n>100: break
            obj = json.loads(line)
            if not need.issubset(obj.keys()):
                missing = need - set(obj.keys())
                raise AssertionError(f"{f.name}: missing keys {missing} in line {n}")
    print("[OK] Fraud logs contract satisfied for", f.name)
    return 0

if __name__ == "__main__":
    sys.exit(main())
