# ===== BEGIN: discover_endpoints.py =====
from __future__ import annotations
import json, re, shlex
from pathlib import Path
from dataclasses import dataclass, asdict

ROOT = Path(r"C:\DevProjects\risk_analysis_flagship")
TASKS_JSON = ROOT / r".vscode\tasks.json"
OUT_JSON = ROOT / r"docs_global\index_servers.json"
OUT_MD   = ROOT / r"docs_global\INDEX_SERVERS.md"

PY_EXE = (ROOT / r".venv\Scripts\python.exe").as_posix()

@dataclass
class Service:
    id: str
    name: str
    kind: str          # "api" | "ui" | "orchestrator" | "other"
    base_url: str
    health_path: str | None = None
    docs_url: str | None = None
    start_label: str | None = None
    start_cmd: str | None = None
    cwd: str | None = None
    env: dict | None = None
    notes: str | None = None
    autostart: bool = True

def slugify(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "svc"

def expand_py_interp(cmd: str) -> str:
    return cmd.replace("${config:python.defaultInterpreterPath}", PY_EXE)

def parse_uvicorn_cmd(cmd: str) -> tuple[str,int] | None:
    if "uvicorn" not in cmd:
        return None
    host = "127.0.0.1"
    port = 8000
    toks = shlex.split(cmd, posix=False)
    for i,t in enumerate(toks):
        if t == "--host" and i+1 < len(toks): host = toks[i+1]
        if t == "--port" and i+1 < len(toks):
            try: port = int(toks[i+1])
            except: pass
    if host == "0.0.0.0": host = "127.0.0.1"
    return host, port

def parse_mlflow_ui_cmd(cmd: str) -> int | None:
    if " mlflow " not in f" {cmd} " or " ui" not in cmd:
        return None
    port = 5000
    toks = shlex.split(cmd, posix=False)
    for i,t in enumerate(toks):
        if t in ("--port","-p") and i+1 < len(toks):
            try: port = int(toks[i+1])
            except: pass
    return port

def discover_from_tasks() -> list[Service]:
    if not TASKS_JSON.exists(): return []
    tasks = json.loads(TASKS_JSON.read_text(encoding="utf-8")).get("tasks", [])
    services: list[Service] = []
    for task in tasks:
        label = task.get("label") or "Task"
        cmd = task.get("command") or ""
        args = task.get("args") or []
        opts = task.get("options") or {}
        env  = opts.get("env") or {}
        cwd  = opts.get("cwd")
        # flatten to a single command line
        full = expand_py_interp(" ".join([cmd] + (args if isinstance(args, list) else [])))

        # uvicorn
        uv = parse_uvicorn_cmd(full)
        if uv:
            host, port = uv
            base = f"http://{host}:{port}"
            services.append(Service(
                id=slugify(label),
                name=label,
                kind="api",
                base_url=base,
                health_path="/health",
                docs_url="/docs",
                start_label=label,
                start_cmd=full,
                cwd=cwd,
                env=env
            ))
            continue

        # mlflow ui
        mlp = parse_mlflow_ui_cmd(full)
        if mlp:
            base = f"http://127.0.0.1:{mlp}"
            services.append(Service(
                id=slugify(label),
                name=label,
                kind="ui",
                base_url=base,
                health_path="/",
                docs_url=None,
                start_label=label,
                start_cmd=full,
                cwd=cwd,
                env=env
            ))
            continue
    return services

def parse_uvicorn_run_text(text: str) -> tuple[str,int] | None:
    # crude extract of host/port from uvicorn.run(...host="x", port=nnn...)
    m_host = re.search(r'uvicorn\.run\([^)]*host\s*=\s*["\']([^"\']+)["\']', text)
    m_port = re.search(r'uvicorn\.run\([^)]*port\s*=\s*(\d+)', text)
    host = (m_host.group(1) if m_host else "127.0.0.1")
    port = (int(m_port.group(1)) if m_port else 8000)
    if host == "0.0.0.0": host = "127.0.0.1"
    return host, port

def discover_from_scripts() -> list[Service]:
    services: list[Service] = []
    patterns = ["**/run_*.py", "**/app/*.py"]
    for pat in patterns:
        for p in ROOT.rglob(pat):
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if "uvicorn.run" not in txt:
                continue
            uv = parse_uvicorn_run_text(txt)
            if not uv: 
                continue
            host, port = uv
            base = f"http://{host}:{port}"
            rel = p.relative_to(ROOT).as_posix()
            services.append(Service(
                id=slugify(rel),
                name=f"Auto: {rel}",
                kind="api",
                base_url=base,
                health_path="/health",
                docs_url="/docs",
                start_label=f"python {rel}",
                start_cmd=f'{PY_EXE} {p.as_posix()}',
                cwd=str(ROOT),
                env={}
            ))
    return services

def dedupe_and_mark(services: list[Service]) -> list[Service]:
    out: list[Service] = []
    owner_by_base = {}
    for s in services:
        base = s.base_url
        if base not in owner_by_base:
            owner_by_base[base] = s.name
            out.append(s)
        else:
            s.autostart = False
            s.notes = f"Duplicate of {owner_by_base[base]} on {base} — autostart disabled."
            out.append(s)
    return out

def write_json(services: list[Service]):
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps([asdict(s) for s in services], indent=2), encoding="utf-8")

def write_md(services: list[Service]):
    lines = ["# Local Services Index", "", "> Generated by `discover_endpoints.py`. Run `generate_server_index.py` to refresh status.", ""]
    # group by base for readability
    for s in services:
        lines.append(f"## {s.name}")
        lines.append(f"- Base: {s.base_url}")
        if s.docs_url:   lines.append(f"- Docs: {s.base_url}{s.docs_url}")
        if s.health_path:lines.append(f"- Health: {s.base_url}{s.health_path}")
        if s.start_label:lines.append(f"- How to start: {s.start_label}")
        lines.append(f"- Autostart: {s.autostart}")
        if s.notes: lines.append(f"- Notes: {s.notes}")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

def main():
    from_tasks   = discover_from_tasks()
    from_scripts = discover_from_scripts()
    services = dedupe_and_mark(from_tasks + from_scripts)
    write_json(services)
    write_md(services)
    print(f"[OK] wrote {OUT_JSON}")
    print(f"[OK] wrote {OUT_MD}")

if __name__ == "__main__":
    main()
# ===== END: discover_endpoints.py =====
