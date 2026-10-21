"""WhatsApp remote for MyDesk (official WhatsApp Cloud API, via your own relay).

MyDesk asks your relay (relay/worker.js) for new messages every few seconds —
an outgoing request only, so nothing on this PC is reachable from the internet —
then runs the command through the same allow-list as the file mailbox and replies
through the WhatsApp Cloud API. Only numbers listed in the relay ever get through.

Commands (send "help" on WhatsApp):
  status · awake 2h · awake until <program> · sleep ok · clip <link> · events
  ports · tools · say <message> · show · help
Replies to your messages are free inside WhatsApp's 24-hour window.
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request

from .config import load_config

HELP = (
    "MyDesk commands:\n"
    "• status — is the PC on, battery, CPU, drives\n"
    "• awake 2h / awake 90m — don't sleep for a while (on charger)\n"
    "• awake until <program> — don't sleep until it finishes\n"
    "• sleep ok — allow normal sleep again\n"
    "• clip <link> — save a reel/video with Clip Maker\n"
    "• events — what's coming up in 15 days\n"
    "• ports — which apps are listening\n"
    "• say <text> — pop a message on the screen\n"
    "• show — bring MyDesk to the front"
)
_state = {"last_poll": None, "last_error": None, "handled": 0}


def parse(text: str) -> dict:
    """WhatsApp text -> mailbox-style request (pure, easy to test)."""
    t = (text or "").strip()
    low = t.lower()
    if low in ("", "help", "hi", "hello", "menu", "?"):
        return {"action": "help"}
    if low in ("status", "on?", "is pc on", "is my pc on", "pc", "ping"):
        return {"action": "status"}
    if low in ("sleep ok", "sleep", "release", "awake off", "stop awake"):
        return {"action": "keep_awake", "release": True}
    m = re.match(r"^awake\s+until\s+(.+)$", low)
    if m:
        return {"action": "keep_awake", "until_exit": m.group(1).strip()}
    m = re.match(r"^awake(?:\s+(\d+(?:\.\d+)?)\s*(h|hr|hrs|hours?|m|min|mins|minutes?)?)?$", low)
    if m:
        n = float(m.group(1) or 1)
        unit = (m.group(2) or "h")[0]
        return {"action": "keep_awake", "minutes": n * 60 if unit == "h" else n}
    m = re.match(r"^(?:clip|save)\s+(https?://\S+)", t, re.I)
    if m:
        return {"action": "run_tool", "tool": "clip_saver", "values": {"url": m.group(1)}, "wait": 3}
    if low in ("events", "calendar", "birthdays"):
        return {"action": "events"}
    if low == "ports":
        return {"action": "ports"}
    if low == "tools":
        return {"action": "list_tools"}
    if low == "show":
        return {"action": "show"}
    m = re.match(r"^(?:say|notify)\s+(.+)$", t, re.I | re.S)
    if m:
        return {"action": "notify", "message": m.group(1).strip()}
    return {"action": "help", "unknown": t[:60]}


def reply_text(req: dict, data) -> str:
    a = req["action"]
    if a == "help":
        return (f"I didn't understand \"{req['unknown']}\".\n\n" if req.get("unknown") else "") + HELP
    if a == "status":
        d = data
        batt = d.get("battery")
        aw = d.get("awake") or {}
        lines = [f"✅ {d.get('computer')} is ON (up {d.get('uptime_hours')} h)",
                 f"CPU {d.get('cpu')}% · memory {d.get('memory')}% · storage {d.get('storage')}%"]
        if batt:
            lines.append(f"Battery {batt['percent']}%{' (charging)' if batt['plugged'] else ' (on battery)'}")
        if aw:
            lines.append(("☕ Staying awake: " if aw.get("holding") else "🌙 Normal sleep: ") + str(aw.get("reason")))
        if d.get("upcoming_events"):
            lines.append("Coming up: " + "; ".join(d["upcoming_events"][:3]))
        return "\n".join(lines)
    if a == "keep_awake":
        if req.get("release"):
            return "🌙 OK — the PC can sleep normally again."
        if not data.get("on_ac"):
            return "🔋 Noted, but the PC is on battery, so it will still sleep. Plug in the charger to keep it awake."
        if req.get("until_exit"):
            return f"☕ Staying awake until {data.get('hold_name') or req['until_exit']} finishes (while on charger)."
        return f"☕ Staying awake for {int(req.get('minutes', 60))} min (while on charger)."
    if a == "run_tool":
        st = data.get("status")
        if st == "done":
            return f"🎬 Clip saved: {(data.get('result') or {}).get('msg', 'done')}"
        if st == "failed":
            return f"⚠️ Clip Maker failed: {data.get('error')}"
        return "🎬 Saving the clip… I'll message you when it's done."
    if a == "events":
        ups = [e for e in data.get("upcoming", []) if not e.get("acked")]
        if not ups:
            return "📅 Nothing in the next 15 days."
        return "📅 Coming up:\n" + "\n".join(f"• {e['title']} — {e['date']} ({'today' if e['days'] == 0 else 'in ' + str(e['days']) + ' d'})" for e in ups[:8])
    if a == "ports":
        net = [p for p in data.get("ports", []) if p["scope"] == "network" and p["proto"] == "TCP"]
        head = f"🔌 {data.get('listening', 0)} listening ports, {len(net)} reachable from your network"
        return head + ("".join(f"\n• {p['port']} {p['app']}" for p in net[:10]) if net else "")
    if a == "list_tools":
        return "🧰 Tools: " + ", ".join(t["name"] for t in data.get("tools", []))
    if a == "notify":
        return "💬 Shown on the screen."
    if a == "show":
        return "🖥️ MyDesk brought to the front." if data.get("shown") else "MyDesk window isn't available right now."
    return "Done."


def _send(cfg: dict, to: str, text: str) -> None:
    w = cfg["whatsapp"]
    url = f"https://graph.facebook.com/{w.get('graph_version', 'v23.0')}/{w['phone_number_id']}/messages"
    body = json.dumps({"messaging_product": "whatsapp", "to": to, "type": "text",
                       "text": {"body": text[:4000], "preview_url": False}}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {w['access_token']}", "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).read()


def _handle(cfg: dict, msg: dict) -> None:
    from . import inbox, system_health

    to = msg["from_number"]
    req = parse(msg.get("body", ""))
    try:
        if req["action"] == "help":
            data = None
        elif req["action"] == "ports":
            data = system_health.ports()
        else:
            data = inbox.handle(dict(req))
        text = reply_text(req, data)
    except Exception as exc:
        text = f"⚠️ {exc}"
    inbox.notify(f"WhatsApp: {msg.get('body', '')[:60]}", source="whatsapp")
    try:
        _send(cfg, to, text)
    except urllib.error.HTTPError as exc:
        _state["last_error"] = f"send failed: {exc.code} {exc.read()[:200]!r}"
    except Exception as exc:
        _state["last_error"] = f"send failed: {exc}"
    _state["handled"] += 1
    # a clip keeps running after the first reply: tell them when it's finished
    if req["action"] == "run_tool" and isinstance(data, dict) and data.get("status") == "running":
        try:
            done = inbox.handle({"action": "job", "job": data["job"], "wait": 140})
            _send(cfg, to, reply_text(req, done))
        except Exception:
            pass


def _pull(cfg: dict) -> list[dict]:
    w = cfg["whatsapp"]
    req = urllib.request.Request(w["relay_url"].rstrip("/") + "/pull", data=b"{}", method="POST", headers={
        "Authorization": f"Bearer {w['relay_key']}", "Content-Type": "application/json", "User-Agent": "MyDesk"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read()).get("messages", [])


def _loop() -> None:
    while True:
        cfg = load_config()
        w = cfg.get("whatsapp") or {}
        wait = max(3, int(w.get("poll_seconds", 5)))
        if w.get("enabled") and all(w.get(k) for k in ("relay_url", "relay_key", "phone_number_id", "access_token")):
            try:
                for msg in _pull(cfg):
                    threading.Thread(target=_handle, args=(cfg, msg), daemon=True).start()
                _state["last_poll"] = time.time()
                _state["last_error"] = None
            except Exception as exc:
                _state["last_error"] = f"relay: {exc}"
                wait = 30   # back off while offline
        else:
            wait = 30
        time.sleep(wait)


def status() -> dict:
    w = load_config().get("whatsapp") or {}
    return {"enabled": bool(w.get("enabled")), **_state}


def start() -> None:
    threading.Thread(target=_loop, name="whatsapp", daemon=True).start()
