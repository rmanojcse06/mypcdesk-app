"""MyDesk — your personal desktop app.

    mydesk                 open MyDesk (or bring the running copy to the front)
    mydesk open --minimized   start minimized (used at sign-in)
    mydesk open --browser     use a Chrome/Edge app window instead of the built-in window
    mydesk serve              run the server only and print its URL
  (from a source checkout: python mydesk.py … works the same)

MyDesk keeps running until you end it in Task Manager: the window's close
button only minimizes it (or hides it to the tray, see "close_button" in
config.json), and a tray icon brings it back. Set "tray_quit": true in
config.json to get a Quit item in the tray menu.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

from mydesk.core import dialogs  # noqa: E402
from mydesk.core import server  # noqa: E402
from mydesk.core.config import DATA_DIR, VERSION, load_config  # noqa: E402

INSTANCE_FILE = DATA_DIR / ".instance.json"
ICON = ROOT / "ui" / "mydesk.png"


# ------------------------------------------------------------------ single instance
def bring_existing_to_front() -> bool:
    """If MyDesk is already running, ask it to show its window and return True."""
    try:
        info = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
        req = urllib.request.Request(info["url"] + "api/show", data=b"{}", method="POST",
                                     headers={"X-MyDesk-Token": info["token"], "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def write_instance_file(url: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    INSTANCE_FILE.write_text(json.dumps({"url": url, "token": server.TOKEN, "pid": os.getpid()}), encoding="utf-8")
    if os.name != "nt":
        os.chmod(INSTANCE_FILE, 0o600)


def title_for(n: int) -> str:
    base = f"MyDesk {VERSION}"
    return f"{base} — {n} dialog{'s' if n != 1 else ''} open" if n else base


# ------------------------------------------------------------------ tray icon
class Tray:
    """System-tray icon: open MyDesk, see/close dialogs, optional Quit."""

    def __init__(self, show, quit_fn=None):
        self.icon = None
        try:
            import pystray
            from PIL import Image
        except Exception as exc:
            print(f"[MyDesk] tray icon unavailable ({exc})")
            return
        items = [
            pystray.MenuItem("Open MyDesk", lambda *_: show(), default=True),
            pystray.MenuItem(lambda _: f"Dialogs open: {dialogs.count()}", None, enabled=False),
            pystray.MenuItem("Close all dialogs", lambda *_: dialogs.close_all(), enabled=lambda _: dialogs.count() > 0),
        ]
        if quit_fn:
            items += [pystray.Menu.SEPARATOR, pystray.MenuItem("Quit MyDesk", lambda *_: quit_fn())]
        try:
            self.icon = pystray.Icon("MyDesk", Image.open(ICON), "MyDesk", pystray.Menu(*items))
            self.icon.run_detached()
        except Exception as exc:
            print(f"[MyDesk] tray icon unavailable ({exc})")
            self.icon = None

    def update(self, n: int) -> None:
        if self.icon:
            try:
                self.icon.title = title_for(n)
                self.icon.update_menu()
            except Exception:
                pass

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass


# ------------------------------------------------------------------ built-in window (pywebview)
class WebviewDialogs:
    """Dialog backend: each dialog is its own native window."""

    def __init__(self, webview, base_url: str):
        self.webview = webview
        self.base = base_url.rstrip("/")
        self.windows: dict = {}

    def open(self, dlg_id: str, title: str, url: str) -> None:
        n = len(self.windows)
        w = self.webview.create_window(title, self.base + url, width=980, height=720, x=140 + 30 * n, y=90 + 30 * n,
                                       min_size=(520, 360), background_color="#FBF6EC", text_select=True)

        def closed(*_):
            self.windows.pop(dlg_id, None)
            dialogs.unregister(dlg_id)

        w.events.closed += closed
        self.windows[dlg_id] = w

    def focus(self, dlg_id: str) -> None:
        w = self.windows.get(dlg_id)
        if w:
            w.restore()
            w.show()
            w.on_top = True   # nudge it in front of other windows
            w.on_top = False

    def close(self, dlg_id: str) -> None:
        w = self.windows.get(dlg_id)
        if w:
            w.destroy()


def run_webview(url: str, cfg: dict, start_minimized: bool) -> bool:
    try:
        import webview  # pywebview: native window (Edge WebView2 on Windows)
    except Exception as exc:
        print(f"[MyDesk] built-in window unavailable ({exc})")
        return False

    state = {"quitting": False}
    main = webview.create_window(f"MyDesk {VERSION}", url, width=cfg["window"]["width"], height=cfg["window"]["height"],
                                 min_size=(1040, 700), minimized=start_minimized,
                                 background_color="#FBF6EC", text_select=True)
    close_to_tray = cfg.get("close_button", "minimize") == "tray"

    def show():
        main.show()
        main.restore()
        main.on_top = True
        main.on_top = False

    def quit_app():
        state["quitting"] = True
        dialogs.close_all()
        tray.stop()
        main.destroy()

    def on_closing():
        if state["quitting"]:
            return True
        # Keep running: the close button minimizes (stays on the taskbar) or hides to the tray.
        if close_to_tray and tray.icon:
            main.hide()
        else:
            main.minimize()
        return False

    tray = Tray(show, quit_app if cfg.get("tray_quit") else None)
    main.events.closing += on_closing
    dialogs.set_backend(WebviewDialogs(webview, url))
    dialogs.on_change(lambda n: (main.set_title(title_for(n)), tray.update(n)))
    server.set_show_window(show)
    try:
        webview.start(private_mode=False, storage_path=str(DATA_DIR / ".webview"))
    except Exception as exc:
        print(f"[MyDesk] built-in window failed ({exc})")
        dialogs.set_backend(None)
        tray.stop()
        return False
    return True


# ------------------------------------------------------------------ fallback: browser app window
def find_app_browser() -> str | None:
    """A Chromium-based browser that supports --app windows (Edge, Chrome, Chromium, Brave)."""
    names = ["msedge", "microsoft-edge", "microsoft-edge-stable", "google-chrome", "google-chrome-stable",
             "chromium", "chromium-browser", "brave-browser", "chrome"]
    paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    for c in [shutil.which(n) for n in names] + paths:
        if c and os.path.exists(c):
            return c
    return None


def run_browser_mode(url: str, cfg: dict, start_minimized: bool) -> None:
    """Server + tray keep running; the window can be closed and reopened from the tray or a relaunch."""
    browser = find_app_browser()
    lock = threading.Lock()
    w, h = cfg["window"]["width"], cfg["window"]["height"]

    def open_window():
        if not lock.acquire(blocking=False):
            return  # already open
        try:
            if browser:
                subprocess.run([browser, f"--app={url}", f"--user-data-dir={DATA_DIR / '.app-window-profile'}",
                                f"--window-size={w},{h}", "--no-first-run", "--no-default-browser-check"])
            else:
                webbrowser.open(url)
        finally:
            lock.release()

    def show():
        threading.Thread(target=open_window, daemon=True).start()

    stop = threading.Event()
    tray = Tray(show, stop.set if cfg.get("tray_quit") else None)
    dialogs.on_change(tray.update)
    server.set_show_window(show)
    if not start_minimized:
        show()
    try:
        stop.wait()
    except KeyboardInterrupt:
        pass
    tray.stop()


# ------------------------------------------------------------------ main
def run_script_and_exit() -> None:
    """Packaged app only: `MyDesk.exe --run-script tool.py args…` runs a tool with the bundled Python."""
    import runpy

    script = sys.argv[2]
    sys.argv = [script, *sys.argv[3:]]
    sys.path.insert(0, str(Path(script).resolve().parent))
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as exc:
        raise SystemExit(exc.code)
    raise SystemExit(0)


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-script":
        run_script_and_exit()
    parser = argparse.ArgumentParser(description="MyDesk desktop app")
    parser.add_argument("--version", action="version", version=f"MyDesk {VERSION}")
    parser.add_argument("--minimized", action="store_true")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    DATA_DIR.mkdir(exist_ok=True)

    if not args.serve and bring_existing_to_front():
        print("[MyDesk] already running — brought it to the front.")
        return

    url = server.start_server()

    if args.serve:
        print(f"MyDesk running at {url}  (Ctrl+C to stop)", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    write_instance_file(url)
    minimized = args.minimized or cfg.get("start_minimized", False)
    if args.browser or not run_webview(url, cfg, minimized):
        run_browser_mode(url, cfg, minimized)


if __name__ == "__main__":
    main()
