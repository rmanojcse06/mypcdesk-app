"""Paths and user settings for MyDesk."""
from __future__ import annotations

import getpass
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_DIR = ROOT / "ui"
TOOLS_DIR = ROOT / "tools"
DATA_DIR = ROOT / "data"
CONFIG_FILE = ROOT / "config.json"  # your settings; not committed (see config.example.json)
SECTIONS_FILE = ROOT / "sections.json"

DEFAULT_CONFIG = {
    "name": "",
    "timezone_label": "",
    "start_minimized": False,
    "window": {"width": 1320, "height": 860},
    "claude_model": "claude-sonnet-5-5",
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
