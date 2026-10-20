"""Run any MyDesk tool from the command line, without opening the app.

    python mytool.py list
    python mytool.py clip_saver "https://youtu.be/XXXX"
    python mytool.py clip_saver URL --cookies-from-browser firefox
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.config import tool_data_dir  # noqa: E402
from core.registry import discover_tools  # noqa: E402


def main() -> None:
    tools = discover_tools()
    if len(sys.argv) < 2 or sys.argv[1] in ("list", "-h", "--help"):
        print("MyDesk tools:\n")
        for t in tools:
            print(f"  {t['id']:<16} {t['name']}  [{t['section']}]")
        print("\nUsage: python mytool.py <tool> [arguments]   (add --help after the tool name for its options)")
        return
    tool = next((t for t in tools if t["id"] == sys.argv[1]), None)
    if not tool:
        sys.exit(f"Unknown tool '{sys.argv[1]}'. Run: python mytool.py list")
    args = sys.argv[2:]
    if "--out" not in args and "-h" not in args and "--help" not in args:
        args += ["--out", str(tool_data_dir(tool["id"]))]
    sys.exit(subprocess.call([sys.executable, tool["script_path"], *args], cwd=str(ROOT)))


if __name__ == "__main__":
    main()
