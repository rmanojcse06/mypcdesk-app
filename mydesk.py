"""MyDesk — your personal desktop app.

    python mydesk.py              open the MyDesk window
    python mydesk.py --minimized  open minimized (used at Windows startup)
    python mydesk.py --browser    open in a Chrome/Edge app window instead of the built-in window
    python mydesk.py --serve      run the server only and print its URL
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.config import DATA_DIR, load_config  # noqa: E402
from core.server import start_server  # noqa: E402


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


def open_in_app_window(url: str, cfg: dict) -> bool:
    """Fallback window: a browser in app mode (no tabs, no address bar)."""
    browser = find_app_browser()
    if not browser:
        webbrowser.open(url)
        print("[MyDesk] opened in your default browser; close this window/terminal to quit.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        return False
    w, h = cfg["window"]["width"], cfg["window"]["height"]
    profile = DATA_DIR / ".app-window-profile"
    proc = subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={profile}",
                             f"--window-size={w},{h}", "--no-first-run", "--no-default-browser-check"])
    proc.wait()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="MyDesk desktop app")
    parser.add_argument("--minimized", action="store_true")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    DATA_DIR.mkdir(exist_ok=True)
    url = start_server()

    if args.serve:
        print(f"MyDesk running at {url}  (Ctrl+C to stop)", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    if not args.browser:
        try:
            import webview  # pywebview: native window using Edge WebView2

            webview.create_window(
                "MyDesk", url, width=cfg["window"]["width"], height=cfg["window"]["height"],
                min_size=(1040, 700), minimized=args.minimized or cfg.get("start_minimized", False),
                background_color="#FBF6EC", text_select=True)
            webview.start(private_mode=False, storage_path=str(DATA_DIR / ".webview"))
            return
        except Exception as exc:  # pywebview missing or WebView2 problem
            print(f"[MyDesk] built-in window unavailable ({exc}); using a browser app window.")
    open_in_app_window(url, cfg)


if __name__ == "__main__":
    main()
