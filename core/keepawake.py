"""Stay awake while Claude is working — only when the charger is connected.

Modes (config "keep_awake", or keep_awake.py --mode):
  "claude-running"  stay awake whenever the Claude desktop app is open        (default)
  "claude-busy"     stay awake while Claude's processes are using CPU, plus a grace period
  "off"             never hold the PC awake on its own
Plus one-off holds that work in any mode: keep awake for N minutes, or until a
program exits (hold_for / hold_until_exit).

On battery nothing is held, so the laptop sleeps normally and saves charge.

How it stops sleep: Windows SetThreadExecutionState (the same call video players
use), macOS `caffeinate -i`, Linux `systemd-inhibit`. It blocks idle sleep only:
you can still sleep, shut down or close the lid yourself (see the README for the
lid-close setting).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time

import psutil

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001

DEFAULT_NAMES = ["claude"]          # matches Claude.exe, claude (Claude Code CLI), etc.
BUSY_CPU = 2.0                      # % of one core, summed over Claude's processes
GRACE_MIN = 15                      # stay awake this long after Claude was last busy
CHECK_EVERY = 15

_lock = threading.Lock()
_state = {"holding": False, "reason": "", "mode": "claude-running", "on_ac": True, "claude": False,
          "busy_cpu": 0.0, "last_busy": 0.0, "hold_until": 0.0, "hold_pid": None, "hold_name": ""}


# ------------------------------------------------------------------ signals
def on_ac_power() -> bool:
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    return True if b is None else bool(b.power_plugged)   # no battery = desktop PC = always "on AC"


def claude_processes(names=None) -> list[psutil.Process]:
    names = [n.lower() for n in (names or DEFAULT_NAMES)]
    me = os.getpid()
    found = []
    for p in psutil.process_iter(["name", "pid"]):
        try:
            n = (p.info["name"] or "").lower()
            if p.info["pid"] != me and any(x in n for x in names):
                found.append(p)
        except psutil.Error:
            continue
    return found


def claude_cpu(procs, sample: float = 1.0) -> float:
    """CPU of Claude's processes and their children, as % of one core."""
    family = []
    for p in procs:
        try:
            family.append(p)
            family.extend(p.children(recursive=True))
        except psutil.Error:
            continue
    for p in family:
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    time.sleep(sample)
    total = 0.0
    for p in family:
        try:
            total += p.cpu_percent(None)
        except psutil.Error:
            pass
    return round(total, 1)


def decide(mode: str, on_ac: bool, claude_open: bool, busy: bool, last_busy: float, now: float,
           hold_until: float = 0, hold_alive: bool = False, grace_min: float = GRACE_MIN) -> tuple[bool, str]:
    """Pure decision: (stay_awake, reason). Easy to test."""
    if not on_ac:
        return False, "on battery: sleeping normally"
    if hold_until > now:
        return True, f"timer: {int((hold_until - now) / 60) + 1} min left"
    if hold_alive:
        return True, "waiting for a program to finish"
    if mode == "claude-running" and claude_open:
        return True, "Claude is open"
    if mode == "claude-busy" and (busy or now - last_busy < grace_min * 60):
        return True, "Claude is working" if busy else "Claude was busy recently"
    return False, "nothing to wait for"


# ------------------------------------------------------------------ platform holders
class _Holder:
    """Owns the OS-level 'don't sleep' request. Must be used from one thread (Windows rule)."""

    def __init__(self):
        self.proc = None
        self.active = False

    def set(self, on: bool) -> None:
        if on == self.active:
            if IS_WIN and on:  # refresh periodically; harmless and survives odd resets
                self._win(True)
            return
        if IS_WIN:
            self._win(on)
        elif IS_MAC and shutil.which("caffeinate"):
            self._proc(["caffeinate", "-i"] if on else None)
        elif shutil.which("systemd-inhibit"):
            self._proc(["systemd-inhibit", "--what=sleep:idle", "--who=MyDesk", "--why=Claude is working",
                        "--mode=block", "sleep", "infinity"] if on else None)
        self.active = on

    def _win(self, on: bool) -> None:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))

    def _proc(self, cmd) -> None:
        if self.proc:
            self.proc.terminate()
            self.proc = None
        if cmd:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ------------------------------------------------------------------ public API
def hold_for(minutes: float) -> None:
    with _lock:
        _state["hold_until"] = max(_state["hold_until"], time.time() + minutes * 60)


def hold_until_exit(target: str) -> str:
    """Keep awake until a program exits: a PID or a process name (first match)."""
    pid = None
    if str(target).isdigit():
        pid = int(target)
    else:
        for p in psutil.process_iter(["name", "pid"]):
            if (p.info["name"] or "").lower().startswith(str(target).lower()):
                pid = p.info["pid"]
                break
    if not pid or not psutil.pid_exists(pid):
        raise ValueError(f"No running program matches '{target}'")
    with _lock:
        _state["hold_pid"] = pid
        _state["hold_name"] = psutil.Process(pid).name()
    return _state["hold_name"]


def release() -> None:
    with _lock:
        _state["hold_until"] = 0
        _state["hold_pid"] = None


def status() -> dict:
    with _lock:
        s = dict(_state)
    s["hold_minutes_left"] = max(0, round((s["hold_until"] - time.time()) / 60))
    return s


def run_loop(mode: str, names=None, stop: threading.Event | None = None, verbose: bool = False) -> None:
    holder = _Holder()
    _state["mode"] = mode
    try:
        while not (stop and stop.is_set()):
            now = time.time()
            procs = claude_processes(names)
            busy_cpu = claude_cpu(procs) if (mode == "claude-busy" and procs) else 0.0
            busy = busy_cpu >= BUSY_CPU
            with _lock:
                if busy:
                    _state["last_busy"] = now
                pid = _state["hold_pid"]
                alive = bool(pid) and psutil.pid_exists(pid)
                if pid and not alive:
                    _state["hold_pid"] = None
                on_ac = on_ac_power()
                awake, reason = decide(_state["mode"], on_ac, bool(procs), busy, _state["last_busy"], now,
                                       _state["hold_until"], alive)
                _state.update(holding=awake, reason=reason, on_ac=on_ac, claude=bool(procs), busy_cpu=busy_cpu)
            holder.set(awake)
            if verbose:
                print(time.strftime("%H:%M:%S"), "AWAKE" if awake else "normal", "-", reason, flush=True)
            (stop.wait(CHECK_EVERY) if stop else time.sleep(CHECK_EVERY))
    finally:
        holder.set(False)


def start(mode: str, names=None) -> None:
    if mode == "off":
        _state["mode"] = "off"
    threading.Thread(target=run_loop, args=(mode, names), name="keep-awake", daemon=True).start()
