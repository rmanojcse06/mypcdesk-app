"""File mailbox: use MyDesk from your phone through Claude, without any network API.

Claude (reached from the Claude app on your phone, linked to this computer by
the Claude desktop app) drops a request into data/inbox/<id>.json. MyDesk picks
it up within ~2 s, does it if the action is on the allow-list below, and writes
the answer to data/outbox/<id>.json. Nothing listens on a port; only someone who
can already write files on this computer can send a request.

Request:  {"id": "a1b2", "action": "run_tool", "tool": "mycheats", "values": {...}, "wait": 60}
Actions:  ping · status · list_tools · run_tool · job · events · ack_event · add_event · notify · show
          (no shell commands, no arbitrary scripts — only tools registered in tools/*/tool.json)
"""
from __future__ import annotations

import json
import re
import threading
import time

from .config import DATA_DIR

INBOX = DATA_DIR / "inbox"
OUTBOX = DATA_DIR / "outbox"
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_WAIT = 150

_notices: list[dict] = []          # shown as pop-ups in the MyDesk window
_lock = threading.Lock()
_show_window = None


def set_show_window(fn) -> None:
    global _show_window
    _show_window = fn


def notify(msg: str, source: str = "phone") -> None:
    with _lock:
        _notices.append({"msg": msg[:300], "source": source, "at": time.time()})
        del _notices[:-20]


def take_notices() -> list[dict]:
    with _lock:
        out = list(_notices)
        _notices.clear()
    return out


def _wait_job(job_id: str, seconds: float) -> dict:
    from . import jobs

    end = time.time() + min(max(seconds, 0), MAX_WAIT)
    job = jobs.get_job(job_id) or {}
    while job.get("status") == "running" and time.time() < end:
        time.sleep(0.5)
        job = jobs.get_job(job_id) or {}
    return {"job": job_id, "status": job.get("status"), "result": job.get("result"), "error": job.get("error"),
            "progress": [e.get("msg") for e in job.get("events", [])][-10:]}


def handle(req: dict) -> dict:
    from . import events, heartbeat, jobs, registry

    action = req.get("action")
    if action == "ping":
        return {"pong": True}
    if action == "status":
        return heartbeat.snapshot()
    if action == "list_tools":
        return {"tools": [{"id": t["id"], "name": t["name"], "section": t["section"],
                           "inputs": [{k: f.get(k) for k in ("name", "label", "type", "required", "options")} for f in t.get("inputs", [])]}
                          for t in registry.discover_tools()]}
    if action == "run_tool":
        tool = registry.get_tool(str(req.get("tool", "")))
        if not tool:
            raise ValueError("unknown tool — use list_tools")
        if tool.get("kind") == "viewer":
            raise ValueError("viewer tools open on screen; use show instead")
        args = registry.build_args(tool, req.get("values") or {})
        job_id = jobs.start_job(tool, args)
        notify(f"Phone (via Claude) started {tool['name']}")
        return _wait_job(job_id, float(req.get("wait", 60)))
    if action == "job":
        return _wait_job(str(req.get("job", "")), float(req.get("wait", 0)))
    if action == "events":
        return events.overview()
    if action == "ack_event":
        events.ack(str(req.get("event_id", "")), str(req.get("date", "")), bool(req.get("undo")))
        return {"ok": True}
    if action == "add_event":
        ev = events.add(req.get("title", ""), req.get("date", ""), req.get("kind", "other"), bool(req.get("yearly")), req.get("note", ""))
        notify(f"Phone (via Claude) added event: {ev['title']}")
        return ev
    if action == "notify":
        notify(str(req.get("message", "")) or "Hello from your phone")
        return {"ok": True}
    if action == "show":
        if _show_window:
            _show_window()
        return {"ok": True, "shown": bool(_show_window)}
    raise ValueError(f"action '{action}' is not allowed")


def _process(path) -> None:
    try:
        req = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        req, err = {}, f"bad request file: {exc}"
    else:
        err = None
    req_id = str(req.get("id") or path.stem)
    if not SAFE_ID.match(req_id):
        req_id = f"req{int(time.time())}"
    try:
        path.unlink()
    except OSError:
        pass
    started = time.time()
    if err:
        resp = {"ok": False, "error": err}
    else:
        try:
            resp = {"ok": True, "data": handle(req)}
        except Exception as exc:  # report every failure back to the sender
            resp = {"ok": False, "error": str(exc)}
    resp.update(id=req_id, action=req.get("action"), finished=time.strftime("%Y-%m-%dT%H:%M:%S"),
                seconds=round(time.time() - started, 2))
    OUTBOX.mkdir(parents=True, exist_ok=True)
    tmp = OUTBOX / f"{req_id}.tmp"
    tmp.write_text(json.dumps(resp, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(OUTBOX / f"{req_id}.json")


def _cleanup() -> None:
    cutoff = time.time() - 86400
    for f in OUTBOX.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass


def _loop() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    last_clean = 0.0
    while True:
        for f in sorted(INBOX.glob("*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0):
            # run each request in its own thread so a long tool doesn't block quick questions
            threading.Thread(target=_process, args=(f,), daemon=True).start()
            time.sleep(0.05)
        if time.time() - last_clean > 3600:
            last_clean = time.time()
            _cleanup()
        time.sleep(1.5)


def start() -> None:
    threading.Thread(target=_loop, name="inbox", daemon=True).start()
