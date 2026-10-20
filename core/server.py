"""Local web server behind the MyDesk window. Listens on 127.0.0.1 only.

Every API call must carry the per-launch token, so web pages you visit in a
normal browser can't talk to MyDesk.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import secrets
import subprocess
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

from . import dialogs, events, jobs, outputs, registry, system_health
from .config import UI_DIR, load_config, load_sections

TOKEN = secrets.token_urlsafe(24)
SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_show_window = None  # set by mydesk.py: brings the main window to the front


def set_show_window(fn) -> None:
    global _show_window
    _show_window = fn


def _run_tool_page(tool: dict, args: list[str], timeout: int = 30) -> str:
    """Viewer tools answer --list-json / --html <name> on stdout."""
    proc = subprocess.run([jobs._python_for_tools(), tool["script_path"], *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          creationflags=jobs.CREATE_NO_WINDOW, cwd=tool["folder"])
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "tool failed").strip()[-400:])
    return proc.stdout


def page_url(tool_id: str, name: str) -> str:
    return f"/page/{quote(tool_id)}/{quote(name)}?t={quote(TOKEN)}"
files_url = outputs.files_url_factory(TOKEN)
mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("image/webp", ".webp")


def _state() -> dict:
    cfg = load_config()
    return {
        "name": cfg["name"],
        "tz": cfg.get("timezone_label", ""),
        "sections": load_sections(),
        "tools": [registry.public_view(t) for t in registry.discover_tools()],
        "claude_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "native_dialogs": dialogs.has_backend(),
    }


def _ask_claude(question: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Set the ANTHROPIC_API_KEY environment variable to chat with Claude.")
    st = _state()
    catalogue = "; ".join(f"{t['name']} ({t['section']}): {t.get('description', '')}" for t in st["tools"])
    body = {
        "model": load_config().get("claude_model", "claude-sonnet-5-5"),
        "max_tokens": 800,
        "system": ("You are the assistant inside MyDesk, a personal desktop dashboard. "
                   f"Available tools: {catalogue}. Answer briefly and point to a tool when one fits."),
        "messages": [{"role": "user", "content": question}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Claude API error {exc.code}: {exc.read().decode(errors='replace')[:300]}")
    return "".join(block.get("text", "") for block in data.get("content", []))


class Handler(BaseHTTPRequestHandler):
    server_version = "MyDesk/1.0"

    def log_message(self, *args) -> None:  # keep the console quiet
        pass

    # ---------- helpers ----------
    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, status: int = 200) -> None:
        self._send(status, json.dumps(data).encode(), "application/json")

    def _authorized(self, query: dict) -> bool:
        return secrets.compare_digest(self.headers.get("X-MyDesk-Token", "") or query.get("t", [""])[0], TOKEN)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}") if length else {}

    # ---------- routes ----------
    def do_GET(self) -> None:
        url = urlparse(self.path)
        q = parse_qs(url.query)
        path = url.path
        if path in ("/", "/index.html"):
            page = (UI_DIR / "index.html").read_text(encoding="utf-8").replace("{{TOKEN}}", TOKEN)
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        if path.startswith("/ui/"):
            target = (UI_DIR / path[4:]).resolve()
            if UI_DIR.resolve() not in target.parents or not target.is_file():
                return self._send(404, b"not found", "text/plain")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            return self._send(200, target.read_bytes(), ctype)
        if not self._authorized(q):
            return self._send(403, b"forbidden", "text/plain")
        try:
            if path.startswith("/files/"):
                return self._file(path)
            if path.startswith("/page/"):
                _, _, tool_id, name = path.split("/", 3)
                tool, name = registry.get_tool(unquote(tool_id)), unquote(name)
                if not tool or not SAFE_NAME.match(name):
                    return self._send(404, b"not found", "text/plain")
                html_page = _run_tool_page(tool, ["--html", name])
                return self._send(200, html_page.encode(), "text/html; charset=utf-8")
            if path == "/api/ping":
                return self._json({"ok": True, "pid": os.getpid()})
            if path == "/api/dialogs":
                return self._json(dialogs.list_dialogs())
            if path == "/api/events":
                return self._json(events.overview())
            if path == "/api/tool-items":
                tool = registry.get_tool(q.get("tool", [""])[0])
                if not tool or tool.get("kind") != "viewer":
                    return self._json([])
                return self._json(json.loads(_run_tool_page(tool, ["--list-json"]) or "[]"))
            if path == "/api/state":
                return self._json(_state())
            if path == "/api/health":
                return self._json(system_health.health())
            if path == "/api/os":
                return self._json(system_health.os_details())
            if path == "/api/ports":
                return self._json(system_health.ports())
            if path == "/api/job":
                job = jobs.get_job(q.get("id", [""])[0])
                return self._json(job or {"error": "unknown job"}, 200 if job else 404)
            if path == "/api/outputs":
                tool = registry.get_tool(q.get("tool", [""])[0])
                return self._json(outputs.list_outputs(tool) if tool else [])
            if path == "/api/render":
                tool = registry.get_tool(q.get("tool", [""])[0])
                if not tool:
                    return self._json({"error": "unknown tool"}, 404)
                return self._json(outputs.render_output(tool, q.get("path", [""])[0], files_url))
        except PermissionError as exc:
            return self._json({"error": str(exc)}, 403)
        except FileNotFoundError:
            return self._json({"error": "not found"}, 404)
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
            return self._json({"error": str(exc)}, 500)
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        url = urlparse(self.path)
        if not self._authorized(parse_qs(url.query)):
            return self._send(403, b"forbidden", "text/plain")
        try:
            body = self._body()
            if url.path == "/api/run":
                tool = registry.get_tool(body.get("tool", ""))
                if not tool:
                    return self._json({"error": "unknown tool"}, 404)
                args = registry.build_args(tool, body.get("values", {}))
                return self._json({"job": jobs.start_job(tool, args)})
            if url.path == "/api/dialogs/open":
                tool = registry.get_tool(body.get("tool", ""))
                name = str(body.get("name", ""))
                if not tool or not SAFE_NAME.match(name):
                    return self._json({"error": "unknown page"}, 404)
                title = str(body.get("title") or f"{tool['name']} · {name}")[:80]
                return self._json(dialogs.open_dialog(title, page_url(tool["id"], name)))
            if url.path == "/api/dialogs/close":
                if body.get("all"):
                    dialogs.close_all()
                else:
                    dialogs.close(str(body.get("id", "")))
                return self._json({"ok": True, "count": dialogs.count()})
            if url.path == "/api/dialogs/focus":
                dialogs.focus(str(body.get("id", "")))
                return self._json({"ok": True})
            if url.path == "/api/events/add":
                ev = events.add(body.get("title", ""), body.get("date", ""), body.get("kind", "other"),
                                bool(body.get("yearly")), body.get("note", ""))
                return self._json(ev)
            if url.path == "/api/events/ack":
                events.ack(str(body.get("id", "")), str(body.get("date", "")), bool(body.get("undo")))
                return self._json({"ok": True})
            if url.path == "/api/events/delete":
                events.delete(str(body.get("id", "")))
                return self._json({"ok": True})
            if url.path == "/api/show":
                if _show_window:
                    _show_window()
                return self._json({"ok": True})
            if url.path == "/api/claude":
                return self._json({"answer": _ask_claude(str(body.get("q", ""))[:4000])})
            if url.path == "/api/open-folder":
                tool = registry.get_tool(body.get("tool", ""))
                if tool and os.name == "nt":
                    target = outputs.safe_path(tool["id"], body.get("path", "."))
                    os.startfile(str(target if target.is_dir() else target.parent))  # noqa: S606
                return self._json({"ok": True})
        except (ValueError, RuntimeError) as exc:
            return self._json({"error": str(exc)}, 400)
        self._send(404, b"not found", "text/plain")

    def _file(self, path: str) -> None:  # noqa: C901
        _, _, tool_id, rel = path.split("/", 3)
        target = outputs.safe_path(unquote(tool_id), unquote(rel))
        if not target.is_file():
            raise FileNotFoundError
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        size = target.stat().st_size
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):  # video seeking
            start_s, _, end_s = rng[6:].partition("-")
            start = int(start_s or 0)
            end = min(int(end_s) if end_s else size - 1, start + 8 * 2**20, size - 1)
            with open(target, "rb") as fh:
                fh.seek(start)
                chunk = fh.read(end - start + 1)
            return self._send(HTTPStatus.PARTIAL_CONTENT, chunk, ctype,
                              {"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes"})
        self._send(200, target.read_bytes(), ctype, {"Accept-Ranges": "bytes"})


def start_server() -> str:
    """Start on a free port in a background thread; returns the app URL."""
    system_health.start_sampler()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, name="mydesk-http", daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}/"
