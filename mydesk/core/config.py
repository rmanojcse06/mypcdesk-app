"""Paths and user settings for MyDesk."""
from __future__ import annotations

import getpass
import json
import os
import sys
from pathlib import Path

# Where things live:
#   code (ROOT)      the mydesk package: ui/, tools/, sections.json — read-only once installed
#   APP_HOME         your settings, data and own tools:
#     source checkout (git clone + install.bat)  -> the repo folder, as before
#     pip/pipx package or standalone executable  -> the usual per-user folder for your system:
#       Windows %APPDATA%\MyDesk · macOS ~/Library/Application Support/MyDesk · Linux ~/.local/share/mydesk
#   MYDESK_HOME overrides APP_HOME; MYDESK_DATA overrides only the data folder.
FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(__file__).resolve().parent.parent          # .../mydesk
REPO = ROOT.parent
SOURCE_TREE = not FROZEN and (REPO / "pyproject.toml").exists() and (REPO / "install.bat").exists()


def _user_home() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "MyDesk"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "MyDesk"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "mydesk"


APP_HOME = Path(os.environ["MYDESK_HOME"]) if os.environ.get("MYDESK_HOME") else (REPO if SOURCE_TREE else _user_home())
UI_DIR = ROOT / "ui"
TOOLS_DIR = ROOT / "tools"
USER_TOOLS_DIR = APP_HOME / "tools"
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
