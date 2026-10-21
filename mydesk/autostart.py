"""Start MyDesk when you sign in — Windows, macOS and Linux.

    mydesk autostart on | off | status
"""
from __future__ import annotations

import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path

NAME = "MyDesk"


def launch_command() -> list[str]:
    """The command that opens MyDesk on this install (frozen exe, pip/pipx command, or source checkout)."""
    if getattr(sys, "frozen", False):
        # register the windowless MyDesk, even when this was run from the console twin MyDesk-tool
        here = Path(sys.executable).parent
        app = here / ("MyDesk.exe" if os.name == "nt" else "MyDesk")
        return [str(app if app.exists() else sys.executable), "--minimized"]
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "python.exe" and (exe.parent / "pythonw.exe").exists():
        exe = exe.parent / "pythonw.exe"           # no console window at sign-in
    return [str(exe), "-m", "mydesk", "open", "--minimized"]


# ---------------------------------------------------------------- Windows: HKCU Run key
def _win(on: bool | None):
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
        if on is None:
            try:
                return winreg.QueryValueEx(k, NAME)[0]
            except FileNotFoundError:
                return None
        if on:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(launch_command()))
        else:
            try:
                winreg.DeleteValue(k, NAME)
            except FileNotFoundError:
                pass


# ---------------------------------------------------------------- macOS: LaunchAgent
def _mac(on: bool | None):
    plist = Path.home() / "Library" / "LaunchAgents" / "com.mydesk.app.plist"
    if on is None:
        return str(plist) if plist.exists() else None
    if on:
        plist.parent.mkdir(parents=True, exist_ok=True)
        with open(plist, "wb") as f:
            plistlib.dump({"Label": "com.mydesk.app", "ProgramArguments": launch_command(), "RunAtLoad": True}, f)
    elif plist.exists():
        plist.unlink()


# ---------------------------------------------------------------- Linux: XDG autostart
def _linux(on: bool | None):
    desktop = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "autostart" / "mydesk.desktop"
    if on is None:
        return str(desktop) if desktop.exists() else None
    if on:
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text("[Desktop Entry]\nType=Application\nName=MyDesk\n"
                           f"Exec={shlex.join(launch_command())}\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
    elif desktop.exists():
        desktop.unlink()


def _impl():
    return _win if os.name == "nt" else _mac if sys.platform == "darwin" else _linux


def enable() -> None:
    _impl()(True)


def disable() -> None:
    _impl()(False)


def status() -> str | None:
    return _impl()(None)
