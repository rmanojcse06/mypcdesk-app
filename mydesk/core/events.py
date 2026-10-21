"""Personal events for the header calendar: birthdays, anniversaries, seminars, bills…

Stored locally in data/events/events.json (never committed). Yearly events
(birthdays) repeat every year. "Acknowledging" marks one occurrence as seen,
so next year's birthday alerts you again.
"""
from __future__ import annotations

import calendar
import datetime as dt
import json
import threading
import uuid

from .config import DATA_DIR

FOLDER = DATA_DIR / "events"
EVENTS_FILE = FOLDER / "events.json"
ACKS_FILE = FOLDER / "acks.json"
KINDS = {"birthday": "🎂", "anniversary": "💐", "seminar": "🎤", "meeting": "👥", "bill": "🧾", "trip": "✈️", "other": "📌"}
WINDOW_DAYS = 15
_lock = threading.Lock()


def _read(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path, data) -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _occurrence(ev: dict, year: int) -> dt.date | None:
    d = dt.date.fromisoformat(ev["date"])
    if not ev.get("yearly"):
        return d if d.year == year else None
    day = d.day
    if d.month == 2 and day == 29 and not calendar.isleap(year):
        day = 28  # Feb 29 birthdays are shown on Feb 28 in other years
    return dt.date(year, d.month, day)


def _item(ev: dict, when: dt.date, today: dt.date, acks: set) -> dict:
    key = f"{ev['id']}@{when.isoformat()}"
    item = {"id": ev["id"], "title": ev["title"], "kind": ev.get("kind", "other"), "icon": KINDS.get(ev.get("kind"), "📌"),
            "date": when.isoformat(), "days": (when - today).days, "yearly": bool(ev.get("yearly")),
            "note": ev.get("note", ""), "acked": key in acks}
    if ev.get("yearly") and ev.get("kind") in ("birthday", "anniversary"):
        start = dt.date.fromisoformat(ev["date"]).year
        if start > 1900 and when.year > start:
            item["years"] = when.year - start  # turns 7 / 10th anniversary
    return item


def overview(today: dt.date | None = None) -> dict:
    """Upcoming (today .. +15 days), earlier this month, and a month map for the mini calendar."""
    today = today or dt.date.today()
    with _lock:
        events = _read(EVENTS_FILE, [])
        acks = set(_read(ACKS_FILE, []))
    horizon = today + dt.timedelta(days=WINDOW_DAYS)
    upcoming, earlier, month_days = [], [], {}
    for ev in events:
        try:
            for year in {today.year, horizon.year}:
                when = _occurrence(ev, year)
                if not when:
                    continue
                if today <= when <= horizon:
                    upcoming.append(_item(ev, when, today, acks))
                elif when.year == today.year and when.month == today.month and when < today:
                    earlier.append(_item(ev, when, today, acks))
                if when.year == today.year and when.month == today.month:
                    month_days.setdefault(when.day, []).append(ev.get("kind", "other"))
        except (KeyError, ValueError):
            continue
    upcoming.sort(key=lambda x: (x["date"], x["title"]))
    earlier.sort(key=lambda x: x["date"], reverse=True)
    pending = [x for x in upcoming if not x["acked"]]
    return {
        "today": today.isoformat(), "window_days": WINDOW_DAYS,
        "upcoming": upcoming, "earlier": earlier, "month_days": month_days,
        "pending": len(pending), "due_soon": sum(1 for x in pending if x["days"] <= 3),
        "total": len(events), "kinds": KINDS,
    }


def add(title: str, date: str, kind: str = "other", yearly: bool = False, note: str = "") -> dict:
    title = (title or "").strip()[:120]
    if not title:
        raise ValueError("Give the event a name.")
    try:
        dt.date.fromisoformat(date)
    except (TypeError, ValueError):
        raise ValueError("Pick a date.")
    ev = {"id": uuid.uuid4().hex[:10], "title": title, "date": date, "kind": kind if kind in KINDS else "other",
          "yearly": bool(yearly), "note": (note or "").strip()[:300]}
    with _lock:
        events = _read(EVENTS_FILE, [])
        events.append(ev)
        _write(EVENTS_FILE, events)
    return ev


def delete(ev_id: str) -> None:
    with _lock:
        events = [e for e in _read(EVENTS_FILE, []) if e.get("id") != ev_id]
        _write(EVENTS_FILE, events)


def ack(ev_id: str, date: str, undo: bool = False) -> None:
    key = f"{ev_id}@{date}"
    with _lock:
        acks = set(_read(ACKS_FILE, []))
        acks.discard(key) if undo else acks.add(key)
        # keep only the last ~2 years of acknowledgements
        cutoff = (dt.date.today() - dt.timedelta(days=730)).isoformat()
        _write(ACKS_FILE, sorted(k for k in acks if k.split("@")[-1] >= cutoff))
