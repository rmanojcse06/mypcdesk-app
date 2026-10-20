#!/usr/bin/env python
"""Is my computer on?  Reads the heartbeat MyDesk writes every 30 seconds.

    python pc_status.py              one-line answer + details
    python pc_status.py --json       machine-readable
    python pc_status.py --folder X   read a MyDesk folder somewhere else (e.g. a synced or linked copy)

Exit code: 0 = on, 1 = probably asleep or MyDesk closed, 2 = off / no heartbeat.
Standard library only, so it runs anywhere Python does.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def verdict(status: dict | None, now: float | None = None) -> tuple[int, str]:
    if not status:
        return 2, "No heartbeat found — MyDesk has never run here, or this isn't the MyDesk folder."
    now = now or time.time()
    age = now - int(status.get("last_seen_epoch", 0))
    interval = int(status.get("interval_seconds", 30))
    if age <= interval * 3:
        return 0, f"ON — {status.get('computer', 'your computer')} checked in {int(age)} s ago."
    mins = age / 60
    when = f"{int(mins)} min" if mins < 120 else f"{mins / 60:.1f} h"
    if age <= 15 * 60:
        return 1, f"PROBABLY ASLEEP or MyDesk closed — last check-in {when} ago."
    return 2, f"OFF or ASLEEP — last check-in {when} ago ({status.get('last_seen')})."


def main() -> None:
    ap = argparse.ArgumentParser(description="Tell whether the computer running MyDesk is on.")
    ap.add_argument("--folder", default=str(HERE), help="MyDesk folder (default: this script's folder)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    f = Path(a.folder) / "data" / "status" / "status.json"
    try:
        status = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        status = None
    code, text = verdict(status)
    if a.json:
        print(json.dumps({"code": code, "verdict": text, "status": status}, indent=2))
    else:
        print(text)
        if status and code == 0:
            batt = status.get("battery")
            print(f"  up {status.get('uptime_hours')} h · CPU {status.get('cpu')}% · memory {status.get('memory')}% · storage {status.get('storage')}%"
                  + (f" · battery {batt['percent']}%{' charging' if batt['plugged'] else ''}" if batt else ""))
            if status.get("drives"):
                print("  drives: " + ", ".join(status["drives"]))
            if status.get("upcoming_events"):
                print("  coming up: " + "; ".join(status["upcoming_events"]))
    sys.exit(code)


if __name__ == "__main__":
    main()
