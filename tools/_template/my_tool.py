#!/usr/bin/env python
"""Template for a new MyDesk tool.

1. Copy this folder:   tools/_template  ->  tools/resume_builder
2. Rename this file and set "script" in tool.json to match.
3. Set "section" in tool.json to one of: os_monitor, my_finance, my_events,
   my_social, my_chest, junkyard, my_mirror, my_block.
4. Restart MyDesk. The tool appears in that section with a form built from "inputs".

MyDesk always passes  --out <data folder>  and  --events.
Print progress with say(); finish with finish(). Anything you save as a
Markdown file matching "outputs.glob" shows up in the tool's library.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVENTS = False


def say(msg: str) -> None:
    print("@@" + json.dumps({"event": "progress", "msg": msg}) if EVENTS else f"• {msg}", flush=True)


def finish(msg: str, open_path: str | None = None) -> None:
    if EVENTS:
        print("@@" + json.dumps({"event": "result", "msg": msg, "open": open_path}), flush=True)
    else:
        print(msg)


def main() -> None:
    global EVENTS
    ap = argparse.ArgumentParser(description="Describe your tool here.")
    ap.add_argument("name", help="an example input")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "data" / "my_tool"))
    ap.add_argument("--events", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    EVENTS = a.events

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    say(f"Working on {a.name}")
    note = out / "notes" / f"{a.name}.md"
    note.parent.mkdir(exist_ok=True)
    note.write_text(f'---\ntitle: "{a.name}"\n---\n# {a.name}\n\nHello from your new tool.\n', encoding="utf-8")
    finish("Done", note.relative_to(out).as_posix())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # report errors to MyDesk instead of crashing silently
        print("@@" + json.dumps({"event": "error", "msg": str(exc)}), flush=True)
        sys.exit(1)
