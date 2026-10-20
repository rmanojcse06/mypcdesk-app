"""Discovers tools: every folder in tools/ with a tool.json is a tool.

A tool is just a script. tool.json tells MyDesk which section it lives in,
what inputs to show in the form, and where its outputs are saved.
Folders starting with "_" (like _template) are ignored.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import TOOLS_DIR


def discover_tools() -> list[dict]:
    tools = []
    for manifest in sorted(TOOLS_DIR.glob("*/tool.json")):
        folder = manifest.parent
        if folder.name.startswith("_"):
            continue
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[MyDesk] skipping {folder.name}: bad tool.json ({exc})")
            continue
        meta.setdefault("id", folder.name)
        meta.setdefault("inputs", [])
        meta["folder"] = str(folder)
        script = folder / meta.get("script", f"{folder.name}.py")
        if not script.exists():
            print(f"[MyDesk] skipping {folder.name}: script {script.name} not found")
            continue
        meta["script_path"] = str(script)
        tools.append(meta)
    return tools


def get_tool(tool_id: str) -> dict | None:
    return next((t for t in discover_tools() if t["id"] == tool_id), None)


def build_args(tool: dict, values: dict) -> list[str]:
    """Turn form values into command-line arguments using the tool's inputs list."""
    positional, options = [], []
    for field in tool.get("inputs", []):
        name = field["name"]
        value = values.get(name)
        if field.get("type") == "checkbox":
            if value:
                options.append(f"--{name}")
            continue
        if value in (None, ""):
            if field.get("required"):
                raise ValueError(f"'{field.get('label', name)}' is required")
            continue
        value = str(value).strip()
        if field.get("positional"):
            positional.append(value)
        else:
            options += [f"--{name}", value]
    return positional + options


def public_view(tool: dict) -> dict:
    keys = ("id", "name", "section", "description", "icon", "inputs", "outputs", "accent", "run_label")
    return {k: tool[k] for k in keys if k in tool}
