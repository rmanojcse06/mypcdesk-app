"""OS health numbers for the top strip and the OS Monitor section (uses psutil)."""
from __future__ import annotations

import datetime as dt
import os
import threading
import time

import psutil

from . import devices

_lock = threading.Lock()
_state: dict = {"processes": [], "net_rate": {"sent": 0.0, "recv": 0.0}}


def _system_drive() -> str:
    if os.name == "nt":
        return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"


def _fmt_time(ts: float | None) -> str | None:
    if not ts:
        return None
    return dt.datetime.fromtimestamp(ts).strftime("%d %b %Y, %I:%M %p")


def _last_sign_in() -> float | None:
    try:
        me = os.environ.get("USERNAME") or os.environ.get("USER")
        sessions = psutil.users()
        mine = [u.started for u in sessions if not me or u.name.lower().endswith(me.lower())]
        times = mine or [u.started for u in sessions]
        return max(times) if times else None
    except Exception:
        return None


def _sampler() -> None:
    """Background loop: process CPU needs two samples, network needs a rate."""
    net_prev = psutil.net_io_counters()
    t_prev = time.time()
    for p in psutil.process_iter():
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    cores = psutil.cpu_count() or 1
    while True:
        time.sleep(2.5)
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                cpu = p.cpu_percent(None) / cores
                mem = p.info["memory_info"].rss if p.info["memory_info"] else 0
                procs.append({"pid": p.info["pid"], "name": p.info["name"] or "?", "cpu": round(cpu, 1), "mem_mb": round(mem / 1048576)})
            except psutil.Error:
                continue
        procs.sort(key=lambda x: (x["cpu"], x["mem_mb"]), reverse=True)
        net_now, t_now = psutil.net_io_counters(), time.time()
        span = max(t_now - t_prev, 0.001)
        rate = {
            "sent": (net_now.bytes_sent - net_prev.bytes_sent) / span,
            "recv": (net_now.bytes_recv - net_prev.bytes_recv) / span,
        }
        net_prev, t_prev = net_now, t_now
        with _lock:
            _state["processes"] = [p for p in procs if p["name"] not in ("System Idle Process", "Idle")][:12]
            _state["net_rate"] = rate


def start_sampler() -> None:
    threading.Thread(target=_sampler, name="health-sampler", daemon=True).start()
    devices.start_device_poller()


def health() -> dict:
    vm = psutil.virtual_memory()
    du = psutil.disk_usage(_system_drive())
    boot = psutil.boot_time()
    return {
        "cpu": round(psutil.cpu_percent(interval=None)),
        "memory": round(vm.percent),
        "memory_detail": f"{vm.used / 2**30:.1f} of {vm.total / 2**30:.1f} GB",
        "storage": round(du.percent),
        "storage_detail": f"{du.free / 2**30:.0f} GB free on {_system_drive()}",
        "last_reboot": _fmt_time(boot),
        "last_sign_in": _fmt_time(_last_sign_in()),
        "uptime_hours": round((time.time() - boot) / 3600, 1),
        "devices": devices.snapshot(),
    }


def os_details() -> dict:
    disks = devices.drives()
    battery = None
    try:
        b = psutil.sensors_battery()
        if b:
            battery = {"percent": round(b.percent), "plugged": bool(b.power_plugged)}
    except Exception:
        pass
    with _lock:
        procs = list(_state["processes"])
        rate = dict(_state["net_rate"])
    freq = psutil.cpu_freq()
    return {
        "processes": procs,
        "disks": disks,
        "battery": battery,
        "net_kbps": {"up": round(rate["sent"] / 1024, 1), "down": round(rate["recv"] / 1024, 1)},
        "cpu_cores": psutil.cpu_count(logical=True),
        "cpu_mhz": round(freq.current) if freq else None,
        "per_cpu": [round(x) for x in psutil.cpu_percent(interval=None, percpu=True)],
    }
