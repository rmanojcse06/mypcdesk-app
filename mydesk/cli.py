"""The `mydesk` command.

    mydesk                         open MyDesk (same as `mydesk open`)
    mydesk open [--minimized] [--browser]
    mydesk serve                   server only, prints its URL
    mydesk tools                   list tools
    mydesk run <tool> [args…]      run a tool from the terminal (e.g. mydesk run clip_saver <link>)
    mydesk cheats [sheet]          open a MyCheats sheet (or list them)
    mydesk status [--json]         is this computer on? (reads MyDesk's heartbeat)
    mydesk ask <action> […]        talk to the running MyDesk through its mailbox
    mydesk awake [--for MIN | --until-exit NAME | --mode …]
    mydesk autostart on|off|status start MyDesk when you sign in
    mydesk backup                  zip your settings and data into the backups folder
    mydesk paths                   where code, settings and data live
    mydesk version
"""
from __future__ import annotations

import subprocess
import sys
import time
import zipfile


def _app(argv):
    from mydesk import app
    sys.argv = ["mydesk", *argv]
    app.main()


def cmd_tools(_argv):
    from mydesk.core.registry import discover_tools
    for t in discover_tools():
        print(f"  {t['id']:<14} {t['name']:<14} [{t['section']}]  {t.get('description', '')[:70]}")
    print("\nRun one:  mydesk run <id> [arguments]   (add --help after the id for its options)")


def cmd_run(argv):
    from mydesk.core import jobs
    from mydesk.core.config import tool_data_dir
    from mydesk.core.registry import discover_tools
    if not argv or argv[0] in ("-h", "--help"):
        return cmd_tools([])
    tool = next((t for t in discover_tools() if t["id"] == argv[0]), None)
    if not tool:
        sys.exit(f"Unknown tool '{argv[0]}'. See: mydesk tools")
    args = argv[1:]
    if tool.get("kind") != "viewer" and "--out" not in args and not {"-h", "--help"} & set(args):
        args += ["--out", str(tool_data_dir(tool["id"]))]
    sys.exit(subprocess.call([*jobs.script_command(tool["script_path"]), *args], env=jobs.tool_env()))


def cmd_cheats(argv):
    cmd_run(["mycheats", *argv])


def cmd_status(argv):
    from mydesk import status
    status.main(argv)


def cmd_ask(argv):
    from mydesk import remote
    remote.main(argv)


def cmd_awake(argv):
    from mydesk import awake
    awake.main(argv)


def cmd_autostart(argv):
    from mydesk import autostart
    what = (argv or ["status"])[0]
    if what == "on":
        autostart.enable()
        print("MyDesk will start when you sign in.")
    elif what == "off":
        autostart.disable()
        print("MyDesk will no longer start at sign-in.")
    else:
        s = autostart.status()
        print(f"Start at sign-in: {'ON (' + s + ')' if s else 'off'}")


def backup(note: str = "manual") -> str:
    """Zip config.json and data/ (skipping large videos) into APP_HOME/backups. Keeps the newest 5."""
    from mydesk.core.config import APP_HOME, CONFIG_FILE, DATA_DIR, VERSION
    folder = APP_HOME / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"mydesk-{VERSION}-{time.strftime('%Y%m%d-%H%M%S')}-{note}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        if CONFIG_FILE.exists():
            z.write(CONFIG_FILE, "config.json")
        if DATA_DIR.exists():
            for f in DATA_DIR.rglob("*"):
                rel = f.relative_to(DATA_DIR)
                if not f.is_file() or rel.parts[0].startswith(".") or rel.parts[0] in ("outbox", "inbox"):
                    continue
                if f.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov") or f.stat().st_size > 50 * 2**20:
                    continue
                z.write(f, f"data/{rel.as_posix()}")
    for old in sorted(folder.glob("mydesk-*.zip"))[:-5]:
        old.unlink()
    return str(out)


def cmd_backup(_argv):
    print(f"Backup saved: {backup()}")


def cmd_paths(_argv):
    from mydesk.core import config as c
    print(f"MyDesk {c.VERSION}")
    print(f"  code:      {c.ROOT}")
    print(f"  settings:  {c.CONFIG_FILE}")
    print(f"  data:      {c.DATA_DIR}")
    print(f"  own tools: {c.USER_TOOLS_DIR}")
    print(f"  mode:      {'standalone executable' if c.FROZEN else 'source checkout' if c.SOURCE_TREE else 'installed package'}")


def cmd_version(_argv):
    from mydesk.core.config import VERSION
    print(f"MyDesk {VERSION}")


COMMANDS = {
    "open": _app, "serve": lambda a: _app(["--serve", *a]), "tools": cmd_tools, "run": cmd_run,
    "cheats": cmd_cheats, "status": cmd_status, "ask": cmd_ask, "awake": cmd_awake,
    "autostart": cmd_autostart, "backup": cmd_backup, "paths": cmd_paths, "version": cmd_version,
}


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--run-script":          # internal: how packaged builds run tool scripts
        from mydesk import app
        sys.argv = ["mydesk", *argv]
        return app.main()
    if argv and argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    if argv and argv[0] in ("-V", "--version"):
        return cmd_version([])
    if not argv or argv[0].startswith("-"):
        return _app(argv)                            # `mydesk` or `mydesk --minimized` opens the app
    cmd = COMMANDS.get(argv[0])
    if not cmd:
        sys.exit(f"Unknown command '{argv[0]}'. Try: mydesk help")
    cmd(argv[1:])


if __name__ == "__main__":
    main()
