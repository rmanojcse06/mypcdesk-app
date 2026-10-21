#!/usr/bin/env python
"""Send MyDesk a request through its file mailbox and wait for the answer.

Used by Claude when you talk to it from your phone: the Claude desktop app links
this folder, Claude runs this script, MyDesk (running on the PC) answers.
No ports, no network API — just files in data/inbox and data/outbox.

    mydesk ask ping
    mydesk ask status
    mydesk ask list_tools
    mydesk ask run_tool --tool clip_saver --values '{"url": "https://youtu.be/..."}' --wait 120
    mydesk ask notify --message "Leaving office, start backups"
    mydesk ask add_event --title "Aarav's birthday" --date 2019-10-23 --kind birthday --yearly
    mydesk ask show
    mydesk ask keep_awake --minutes 120        (or --until-exit python, or --release)
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path



def data_dir(folder: Path | None = None) -> Path:
    if folder:
        return Path(folder) / "data"
    from mydesk.core.config import DATA_DIR
    return DATA_DIR


def ask(folder: Path | None, request: dict, timeout: float) -> dict:
    data = data_dir(folder)
    inbox, outbox = data / "inbox", data / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    req_id = request.setdefault("id", "r" + uuid.uuid4().hex[:10])
    request.setdefault("from", "claude")
    tmp = inbox / f"{req_id}.part"
    tmp.write_text(json.dumps(request), encoding="utf-8")
    tmp.rename(inbox / f"{req_id}.json")          # appears all at once, never half-written
    answer = outbox / f"{req_id}.json"
    end = time.time() + timeout
    while time.time() < end:
        if answer.exists():
            try:
                return json.loads(answer.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass  # still being written
        time.sleep(0.5)
    return {"ok": False, "id": req_id, "error": f"No answer within {int(timeout)} s — is MyDesk running? (mydesk status)"}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Ask the MyDesk running on this PC to do something.")
    ap.add_argument("action", choices=["ping", "status", "list_tools", "run_tool", "job", "events", "ack_event",
                                       "add_event", "notify", "show", "keep_awake"])
    ap.add_argument("--tool"); ap.add_argument("--values", default="{}"); ap.add_argument("--job")
    ap.add_argument("--wait", type=float, default=60, help="seconds MyDesk waits for a tool to finish")
    ap.add_argument("--message"); ap.add_argument("--title"); ap.add_argument("--date"); ap.add_argument("--kind", default="other")
    ap.add_argument("--yearly", action="store_true"); ap.add_argument("--note", default="")
    ap.add_argument("--event-id"); ap.add_argument("--undo", action="store_true")
    ap.add_argument("--minutes", type=float); ap.add_argument("--until-exit"); ap.add_argument("--release", action="store_true")
    ap.add_argument("--folder", help="a MyDesk folder (default: this computer's MyDesk)")
    ap.add_argument("--timeout", type=float, default=None, help="seconds to wait for the answer")
    a = ap.parse_args(argv)

    req = {"action": a.action}
    if a.action == "run_tool":
        req.update(tool=a.tool, values=json.loads(a.values), wait=a.wait)
    elif a.action == "job":
        req.update(job=a.job, wait=a.wait)
    elif a.action == "notify":
        req.update(message=a.message or "")
    elif a.action == "add_event":
        req.update(title=a.title, date=a.date, kind=a.kind, yearly=a.yearly, note=a.note)
    elif a.action == "keep_awake":
        req.update(minutes=a.minutes or 60, until_exit=a.until_exit, release=a.release)
    elif a.action == "ack_event":
        req.update(event_id=a.event_id, date=a.date, undo=a.undo)
    timeout = a.timeout or (a.wait + 20 if a.action in ("run_tool", "job") else 20)
    resp = ask(Path(a.folder) if a.folder else None, req, timeout)
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    sys.exit(0 if resp.get("ok") else 1)


if __name__ == "__main__":
    main()
