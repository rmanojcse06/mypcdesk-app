"""Source-checkout shortcut: `python mytool.py <tool> [args]` == `mydesk run <tool> [args]`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mydesk.cli import cmd_run, cmd_tools  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    cmd_tools([]) if not args or args[0] in ("list", "-h", "--help") else cmd_run(args)
