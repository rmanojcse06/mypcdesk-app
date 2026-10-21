#!/usr/bin/env python
"""Keep this PC from sleeping while Claude works — only while the charger is connected.

    python keep_awake.py                         stay awake whenever the Claude app is open (on charger)
    python keep_awake.py --mode claude-busy      only while Claude is actually working, plus 15 min grace
    python keep_awake.py --for 120               stay awake for 2 hours (on charger)
    python keep_awake.py --until-exit python     stay awake until a program finishes (name or PID)
    python keep_awake.py --status                one check, then exit

MyDesk runs the same logic in the background (config "keep_awake"), so you only
need this script when MyDesk isn't running. Press Ctrl+C to stop; the PC can
then sleep normally again. On battery it never holds the PC awake.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import keepawake  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Stay awake while Claude works (charger only).")
    ap.add_argument("--mode", default="claude-running", choices=["claude-running", "claude-busy", "off"])
    ap.add_argument("--for", dest="minutes", type=float, help="also stay awake for this many minutes")
    ap.add_argument("--until-exit", metavar="NAME_OR_PID", help="also stay awake until this program exits")
    ap.add_argument("--names", default="claude", help="comma-separated process names that count as Claude")
    ap.add_argument("--status", action="store_true", help="print one decision and exit")
    a = ap.parse_args()
    names = [n.strip() for n in a.names.split(",") if n.strip()]

    if a.status:
        procs = keepawake.claude_processes(names)
        busy = keepawake.claude_cpu(procs) if procs else 0.0
        awake, why = keepawake.decide(a.mode, keepawake.on_ac_power(), bool(procs), busy >= keepawake.BUSY_CPU, 0, time.time())
        print(f"{'Would stay AWAKE' if awake else 'Would sleep normally'} — {why}. "
              f"Charger: {'yes' if keepawake.on_ac_power() else 'no'} · Claude processes: {len(procs)} · Claude CPU: {busy}%")
        return
    if a.minutes:
        keepawake.hold_for(a.minutes)
    if a.until_exit:
        print(f"Waiting for {keepawake.hold_until_exit(a.until_exit)} to finish.")
    stop = threading.Event()
    one_shot = bool(a.minutes or a.until_exit) and a.mode == "off"
    print("Keeping the PC awake while needed (charger only). Ctrl+C to stop.")
    t = threading.Thread(target=keepawake.run_loop, args=(a.mode, names, stop, True), daemon=True)
    t.start()
    try:
        while t.is_alive():
            time.sleep(1)
            s = keepawake.status()
            if one_shot and not s["hold_minutes_left"] and not s["hold_pid"]:
                print("Done — the PC can sleep normally again.")
                break
    except KeyboardInterrupt:
        pass
    stop.set()
    t.join(timeout=20)


if __name__ == "__main__":
    main()
