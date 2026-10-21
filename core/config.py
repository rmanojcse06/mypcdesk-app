"""Paths and user settings for MyDesk."""
from __future__ import annotations

import getpass
import json
import os
import sys
from pathlib import Path

# Source checkout: everything lives next to the code.
# Packaged app (PyInstaller): code is read-only in the install folder, while your
# settings, data and own tools live in %APPDATA%\MyDesk so updates never touch them.
FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(__file__).resolve().parent.parent
APP_HOME = (Path(os.environ.get("APPDATA") or Path.home()) / "MyDesk") if FROZEN else ROOT
UI_DIR = ROOT / "ui"
TOOLS_DIR = ROOT / "tools"
USER_TOOLS_DIR = APP_HOME / "tools" if FROZEN else ROOT / "tools"
DATA_DIR = Path(os.environ.get("MYDESK_DATA") or APP_HOME / "data")
CONFIG_FILE = APP_HOME / "config.json"  # your settings; not committed (see config.example.json)
SECTIONS_FILE = ROOT / "sections.json"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "dev"

DEFAULT_CONFIG = {
    "name": "",
    "timezone_label": "",
    "start_minimized": False,
    "close_button": "minimize",   # "minimize" keeps it on the taskbar, "tray" hides it to the tray icon
    "tray_quit": False,           # True adds "Quit MyDesk" to the tray menu; otherwise end it in Task Manager
    "window": {"width": 1320, "height": 860},
    "keep_awake": "claude-running",  # stay awake on charger while Claude is open; "claude-busy" or "off"
    "heartbeat_url": "",          # optional healthchecks.io-style check-in URL; alerts your phone when the PC stops
    "claude_model": "claude-sonnet-5-5",
    "whatsapp": {                 # see relay/README.md — official WhatsApp Cloud API via your own relay
        "enabled": False, "relay_url": "", "relay_key": "",
        "phone_number_id": "", "access_token": "", "graph_version": "v23.0", "poll_seconds": 5,
    },
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    if not cfg.get("name"):
        try:
            cfg["name"] = getpass.getuser().split("\\")[-1].title()
        except Exception:
            cfg["name"] = "there"
    return cfg


def load_sections() -> list[dict]:
    return json.loads(SECTIONS_FILE.read_text(encoding="utf-8"))["sections"]


def tool_data_dir(tool_id: str) -> Path:
    path = DATA_DIR / tool_id
    path.mkdir(parents=True, exist_ok=True)
    return path
