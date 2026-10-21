"""Dialog windows opened by MyDesk (e.g. a MyCheats cheatsheet).

The desktop window (mydesk.py) registers a backend that opens real windows.
Without one (browser or --serve mode) the UI shows dialogs as in-page pop-ups
and registers them here itself, so the count is always right.
"""
from __future__ import annotations

import itertools
import threading
import time

_lock = threading.Lock()
_dialogs: dict[str, dict] = {}
_ids = itertools.count(1)
_backend = None          # object with open(id, title, url), focus(id), close(id)
_listeners: list = []    # callables(count) — e.g. update the main window title


def set_backend(backend) -> None:
    global _backend
    _backend = backend


def has_backend() -> bool:
    return _backend is not None


def on_change(fn) -> None:
    _listeners.append(fn)


def _notify() -> None:
    n = count()
    for fn in list(_listeners):
        try:
            fn(n)
        except Exception:
            pass


def register(title: str, url: str, inline: bool = False) -> str:
    dlg_id = f"d{next(_ids)}"
    with _lock:
        _dialogs[dlg_id] = {"id": dlg_id, "title": title, "url": url, "inline": inline, "opened": time.time()}
    _notify()
    return dlg_id


def unregister(dlg_id: str) -> None:
    with _lock:
        removed = _dialogs.pop(dlg_id, None)
    if removed:
        _notify()


def open_dialog(title: str, url: str) -> dict:
    """Open a dialog. Returns {"id", "inline"}; inline=True means the UI must show it itself."""
    if _backend is None:
        return {"id": register(title, url, inline=True), "inline": True}
    dlg_id = register(title, url)
    try:
        _backend.open(dlg_id, title, url)
    except Exception:
        unregister(dlg_id)
        raise
    return {"id": dlg_id, "inline": False}


def focus(dlg_id: str) -> None:
    if _backend is not None and dlg_id in _dialogs and not _dialogs[dlg_id]["inline"]:
        _backend.focus(dlg_id)


def close(dlg_id: str) -> None:
    d = _dialogs.get(dlg_id)
    if not d:
        return
    if _backend is not None and not d["inline"]:
        _backend.close(dlg_id)  # backend calls unregister when the window is gone
    else:
        unregister(dlg_id)


def close_all() -> None:
    for d in list_dialogs():
        close(d["id"])


def list_dialogs() -> list[dict]:
    with _lock:
        return sorted(_dialogs.values(), key=lambda d: d["opened"])


def count() -> int:
    with _lock:
        return len(_dialogs)
