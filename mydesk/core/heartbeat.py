"""Heartbeat: lets you (or Claude, from your phone) tell whether this computer is on.

Every 30 s MyDesk writes data/status/status.json — when it was last seen, uptime,
CPU, memory, battery, drives, open dialogs and upcoming events. Nothing listens
on the network; the file is read through the Claude desktop app's folder link
or by `python pc_status.py`.

Optional: set "heartbeat_url" in config.json to a check-in URL from a free
monitoring service such as healthchecks.io. MyDesk then sends one outgoing
request every 5 minutes, and that service alerts your phone when they stop —
which is the only way to learn the PC went off while you're away from it.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import platform
import socket
import threading
import time
import urllib.request

from .config import DATA_DIR, VERSION, load_config

STATUS_DIR = DATA_DIR / "status"
STATUS_FILE = STATUS_DIR / "status.json"
INTERVAL = 30
PING_EVERY = 300


def snapshot() -> dict:
    from . import dialogs, events, system_health  # late import: avoids cycles at startup

    h = system_health.health()
    dev = h.get("devices") or {}
    try:
        ev = events.overview()
        upcoming = [f"{e['title']} ({e['date']})" for e in ev["upcoming"] if not e["acked"]][:5]
    except Exception:
        upcoming = []
    battery = None
    try:
        import psutil

        b = psutil.sensors_battery()
        if b:
            battery = {"percent": round(b.percent), "plugged": bool(b.power_plugged)}
    except Exception:
        pass
    return {
        "last_seen": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "last_seen_epoch": int(time.time()),
        "computer": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "mydesk_version": VERSION,
        "mydesk_pid": os.getpid(),
        "uptime_hours": h.get("uptime_hours"),
        "last_reboot": h.get("last_reboot"),
        "cpu": h.get("cpu"), "memory": h.get("memory"), "storage": h.get("storage"),
        "battery": battery,
        "drives": [f"{d['name']} {d['percent']}%{' (USB)' if d['kind'] == 'usb' else ''}" for d in dev.get("drives") or []],
        "usb_devices": [d["name"] for d in dev.get("usb") or []],
        "locks": dev.get("locks"),
        "dialogs_open": dialogs.count(),
        "upcoming_events": upcoming,
        "interval_seconds": INTERVAL,
        "awake": _awake(),
    }


def _awake() -> dict:
    from . import keepawake
    s = keepawake.status()
    return {"holding": s["holding"], "reason": s["reason"], "on_charger": s["on_ac"], "mode": s["mode"]}


def write_status() -> None:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot(), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATUS_FILE)


def _ping(url: str) -> None:
    try:
        urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "MyDesk-heartbeat"}), timeout=10).read(64)
    except Exception:
        pass  # offline is exactly what the monitoring service should notice


def _loop() -> None:
    last_ping = 0.0
    while True:
        try:
            write_status()
        except Exception as exc:
            print(f"[MyDesk] heartbeat write failed: {exc}")
        url = (load_config().get("heartbeat_url") or "").strip()
        if url.startswith("https://") and time.time() - last_ping >= PING_EVERY:
            last_ping = time.time()
            threading.Thread(target=_ping, args=(url,), daemon=True).start()
        time.sleep(INTERVAL)


def start() -> None:
    threading.Thread(target=_loop, name="heartbeat", daemon=True).start()
