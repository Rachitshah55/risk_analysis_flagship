# ===== BEGIN: launch_all_servers.py =====
from __future__ import annotations
import json, os, signal, subprocess, sys, time
from pathlib import Path
from typing import Dict

ROOT = Path(r"C:\DevProjects\risk_analysis_flagship")
IN_JSON = ROOT / r"docs_global\index_servers.json"
PIDS_JSON = ROOT / r"docs_global\servers.pids.json"

def load_services():
    if not IN_JSON.exists():
        raise SystemExit(f"[ERR] Missing {IN_JSON}. Run discover_endpoints.py first.")
    return json.loads(IN_JSON.read_text(encoding="utf-8"))

def save_pids(pids: Dict[str,int]):
    PIDS_JSON.parent.mkdir(parents=True, exist_ok=True)
    PIDS_JSON.write_text(json.dumps(pids, indent=2), encoding="utf-8")

def load_pids() -> Dict[str,int]:
    if not PIDS_JSON.exists(): return {}
    return json.loads(PIDS_JSON.read_text(encoding="utf-8"))

def start_all():
    svcs = load_services()
    # avoid port collisions by base_url
    seen_bases = set()
    pids = {}
    for s in svcs:
        if not s.get("autostart", True): continue
        base = s["base_url"]
        if base in seen_bases:
            print(f"[SKIP] Duplicate base {base} for {s['name']}")
            continue
        cmd = s.get("start_cmd")
        if not cmd:
            print(f"[SKIP] No start_cmd for {s['name']}")
            continue
        cwd = s.get("cwd") or str(ROOT)
        env = os.environ.copy()
        env.update(s.get("env") or {})
        print(f"[START] {s['name']} → {cmd}")
        # use shell=True for compound commands; Windows-friendly
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, shell=True)
        pids[s["id"]] = proc.pid
        seen_bases.add(base)
        time.sleep(0.5)  # small stagger
    save_pids(pids)
    print(f"[OK] Started {len(pids)} service(s). PIDs saved to {PIDS_JSON}")

def stop_all():
    pids = load_pids()
    if not pids:
        print("[INFO] No PIDs recorded; nothing to stop.")
        return
    for sid, pid in pids.items():
        try:
            print(f"[STOP] {sid} (pid={pid})")
            # Windows: use taskkill
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print(f"[WARN] Failed to stop {sid}: {e}")
    try:
        PIDS_JSON.unlink(missing_ok=True)
    except Exception:
        pass
    print("[OK] Stop requested for all recorded processes.")

def status():
    try:
        import urllib.request
        def up(u, t=1.5):
            try:
                with urllib.request.urlopen(u, timeout=t) as r:
                    return 200 <= r.status < 400
            except Exception:
                return False
    except Exception:
        def up(u, t=1.5): return False

    svcs = load_services()
    for s in svcs:
        health = s["base_url"] + (s.get("health_path") or "")
        print(f"{s['name']:<28} {health:<45} {'UP' if up(health) else 'DOWN'}")

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("start","stop","status"):
        print("Usage: python launch_all_servers.py [start|stop|status]")
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "start":  start_all()
    if cmd == "stop":   stop_all()
    if cmd == "status": status()

if __name__ == "__main__":
    main()
# ===== END: launch_all_servers.py =====
