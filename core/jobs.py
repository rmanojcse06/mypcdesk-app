"""Runs tool scripts as separate processes and collects their progress.

Tools report progress by printing lines that start with "@@" followed by JSON,
e.g.  @@{"event": "progress", "msg": "Downloading video"}
and finish with  @@{"event": "result", ...}.  Any other output is kept as log text.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid

from .config import DATA_DIR, FROZEN, ROOT, tool_data_dir

_jobs: dict[str, dict] = {}
_lock = threading.Lock()

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _python_for_tools() -> str:
    """Use console python (not pythonw) so stdout can be captured."""
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        candidate = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.exists(candidate):
            return candidate
    return exe


def script_command(script_path: str) -> list[str]:
    """How to run a tool script: with Python from source, or through MyDesk.exe when packaged."""
    if FROZEN:
        # MyDesk-tool.exe is the console twin of MyDesk.exe, so the tool's progress output can be read
        twin = os.path.join(os.path.dirname(sys.executable), "MyDesk-tool.exe")
        return [twin if os.path.exists(twin) else sys.executable, "--run-script", script_path]
    return [_python_for_tools(), script_path]


def tool_env() -> dict:
    return dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", MYDESK_DATA=str(DATA_DIR))


def start_job(tool: dict, args: list[str]) -> str:
    job_id = uuid.uuid4().hex[:12]
    out_dir = tool_data_dir(tool["id"])
    cmd = [*script_command(tool["script_path"]), *args, "--out", str(out_dir), "--events"]
    job = {"id": job_id, "tool": tool["id"], "status": "running", "started": time.time(),
           "events": [], "log": [], "result": None, "error": None}
    with _lock:
        _jobs[job_id] = job
    threading.Thread(target=_run, args=(job, cmd), daemon=True).start()
    return job_id


def _run(job: dict, cmd: list[str]) -> None:
    env = tool_env()
    try:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", env=env,
                                creationflags=CREATE_NO_WINDOW)
    except OSError as exc:
        job.update(status="failed", error=str(exc))
        return
    for line in proc.stdout:
        line = line.rstrip()
        if line.startswith("@@"):
            try:
                event = json.loads(line[2:])
            except json.JSONDecodeError:
                job["log"].append(line)
                continue
            if event.get("event") == "result":
                job["result"] = event
            elif event.get("event") == "error":
                job["error"] = event.get("msg")
            else:
                job["events"].append(event)
        elif line:
            job["log"].append(line)
            del job["log"][:-200]
    code = proc.wait()
    if job["result"] and code == 0:
        job["status"] = "done"
    else:
        job["status"] = "failed"
        job["error"] = job["error"] or (job["log"][-1] if job["log"] else f"exit code {code}")


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
    return dict(job) if job else None
