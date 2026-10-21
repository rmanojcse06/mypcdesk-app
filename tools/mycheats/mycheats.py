#!/usr/bin/env python
"""MyCheats — your cheatbook of commands.

Cheatsheets are Markdown files:
    tools/mycheats/sheets/*.md         sheets that ship with MyDesk
    data/mycheats/sheets/*.md          your own sheets (private, not committed)

A sheet looks like:
    ---
    title: Git
    color: "#f05032"
    ---
    ## Branches
    - `git switch -c <name>` : create a branch and switch to it

Run on its own:
    python mycheats.py                 list sheets
    python mycheats.py git             open the Git sheet in your browser
    python mycheats.py --new docker    create data/mycheats/sheets/docker.md to fill in
MyDesk uses:  --list-json  and  --html <name>
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUILTIN = HERE / "sheets"
DATA = Path(os.environ["MYDESK_DATA"]) if os.environ.get("MYDESK_DATA") else ROOT / "data"
USER = DATA / "mycheats" / "sheets"
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ITEM_RE = re.compile(r"^[-*]\s+`(?P<cmd>.+?)`\s*(?::|—|-)\s*(?P<desc>.*)$")


def sheet_files() -> dict[str, Path]:
    files = {}
    for folder in (BUILTIN, USER):  # your own sheets override built-in ones with the same name
        if folder.exists():
            for f in sorted(folder.glob("*.md")):
                if NAME_RE.match(f.stem):
                    files[f.stem] = f
    return files


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta = {"title": path.stem.replace("-", " ").title(), "color": "#e5484d", "blurb": ""}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip('"')
        text = text[m.end():]
    sections, current = [], None
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            current = {"name": line[3:].strip(), "items": []}
            sections.append(current)
            continue
        im = ITEM_RE.match(line)
        if im:
            if current is None:
                current = {"name": "Commands", "items": []}
                sections.append(current)
            current["items"].append({"cmd": im.group("cmd"), "desc": im.group("desc").strip()})
    meta["sections"] = sections
    meta["count"] = sum(len(s["items"]) for s in sections)
    meta["user"] = path.parent == USER
    return meta


def safe_color(c: str) -> str:
    return c if re.fullmatch(r"#[0-9a-fA-F]{3,8}", c or "") else "#e5484d"


def inline_code(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(text))


def render(name: str) -> str:
    files = sheet_files()
    if name not in files:
        raise SystemExit(f"No cheatsheet called '{name}'. Available: {', '.join(files) or 'none'}")
    s = parse(files[name])
    color = safe_color(s["color"])
    nav = "".join(f'<a href="#s{i}">{html.escape(sec["name"])}</a>' for i, sec in enumerate(s["sections"]))
    body = []
    for i, sec in enumerate(s["sections"]):
        rows = "".join(
            f'<div class="row" data-k="{html.escape((it["cmd"] + " " + it["desc"]).lower())}">'
            f'<code class="cmd">{html.escape(it["cmd"])}</code>'
            f'<span class="desc">{inline_code(it["desc"])}</span>'
            f'<button class="copy" data-cmd="{html.escape(it["cmd"])}" title="Copy command">Copy</button></div>'
            for it in sec["items"])
        body.append(f'<section id="s{i}"><h2>{html.escape(sec["name"])}<small>{len(sec["items"])}</small></h2>{rows}</section>')
    return PAGE.format(title=html.escape(s["title"]), color=color, blurb=html.escape(s.get("blurb", "")),
                       count=s["count"], nav=nav, body="".join(body))


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} · MyCheats</title>
<style>
:root {{ --c: {color}; --ink: #1d2233; --ink2: #565d73; --ink3: #8a90a3; --line: #e7e1d4; --paper: #fbf6ec; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font: 14px/1.45 "Segoe UI", system-ui, sans-serif; }}
header {{ position: sticky; top: 0; z-index: 2; background: #fff; border-bottom: 2.5px solid var(--ink); padding: 14px 22px 10px; }}
.top {{ display: flex; align-items: center; gap: 12px; }}
.badge {{ width: 36px; height: 36px; border-radius: 10px; background: var(--c); border: 2px solid var(--ink); box-shadow: 2px 2px 0 var(--ink);
  display: grid; place-items: center; color: #fff; font: 700 17px Cambria, Georgia, serif; }}
h1 {{ margin: 0; font: 700 22px Cambria, Georgia, serif; }}
.blurb {{ color: var(--ink2); font-size: 12.5px; }}
#q {{ margin-left: auto; width: min(340px, 45vw); padding: 9px 12px; border: 2px solid var(--ink); border-radius: 10px; font: inherit; background: #fffdf8; }}
#q:focus {{ outline: 3px solid color-mix(in srgb, var(--c) 35%, transparent); }}
nav {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }}
nav a {{ padding: 2px 10px; border: 1.5px solid var(--ink); border-radius: 99px; color: var(--ink); text-decoration: none; font-size: 12px; font-weight: 600; background: #fff; }}
nav a:hover {{ background: color-mix(in srgb, var(--c) 15%, #fff); }}
main {{ padding: 8px 22px 30px; max-width: 1100px; }}
h2 {{ font: 700 16px Cambria, Georgia, serif; margin: 20px 0 6px; display: flex; gap: 8px; align-items: baseline; }}
h2::before {{ content: ""; width: 10px; height: 10px; border-radius: 3px; background: var(--c); border: 1.5px solid var(--ink); align-self: center; }}
h2 small {{ font: 600 11px "Segoe UI", sans-serif; color: var(--ink3); }}
.row {{ display: grid; grid-template-columns: minmax(260px, 46%) 1fr auto; gap: 14px; align-items: center;
  padding: 7px 10px; border: 1.5px solid var(--line); border-radius: 10px; background: #fff; margin: 5px 0; }}
.row:hover {{ border-color: var(--ink); }}
.cmd {{ font: 13px/1.4 "Cascadia Mono", Consolas, monospace; background: #f3efe5; padding: 4px 8px; border-radius: 7px; overflow-wrap: anywhere; }}
.desc {{ color: var(--ink2); }}
.desc code {{ font: 12px Consolas, monospace; background: #f3efe5; padding: 1px 4px; border-radius: 4px; }}
.copy {{ padding: 4px 10px; border: 1.5px solid var(--ink); border-radius: 8px; background: #fff; font: 600 12px inherit; cursor: pointer; box-shadow: 1.5px 1.5px 0 var(--ink); }}
.copy.done {{ background: var(--c); color: #fff; }}
.hide {{ display: none; }}
.empty {{ padding: 30px; text-align: center; color: var(--ink3); }}
mark {{ background: color-mix(in srgb, var(--c) 28%, #fff); color: inherit; border-radius: 3px; }}
</style></head><body>
<header><div class="top"><div class="badge">{title[0]}</div><div><h1>{title}</h1><div class="blurb">{blurb} · {count} commands</div></div>
<input id="q" type="search" placeholder="Search {count} commands…  (press / )" autofocus></div><nav>{nav}</nav></header>
<main>{body}<div class="empty hide" id="empty">No commands match.</div></main>
<script>
const q = document.getElementById("q");
q.addEventListener("input", () => {{
  const t = q.value.trim().toLowerCase(); let shown = 0;
  document.querySelectorAll("section").forEach(sec => {{
    let n = 0;
    sec.querySelectorAll(".row").forEach(r => {{ const ok = !t || r.dataset.k.includes(t); r.classList.toggle("hide", !ok); n += ok; }});
    sec.classList.toggle("hide", n === 0); shown += n;
  }});
  document.getElementById("empty").classList.toggle("hide", shown > 0);
}});
document.addEventListener("keydown", e => {{ if (e.key === "/" && document.activeElement !== q) {{ e.preventDefault(); q.focus(); }}
  if (e.key === "Escape") {{ q.value = ""; q.dispatchEvent(new Event("input")); }} }});
document.addEventListener("click", async e => {{
  const b = e.target.closest(".copy"); if (!b) return;
  try {{ await navigator.clipboard.writeText(b.dataset.cmd); }}
  catch {{ const ta = document.createElement("textarea"); ta.value = b.dataset.cmd; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }}
  b.textContent = "Copied"; b.classList.add("done"); setTimeout(() => {{ b.textContent = "Copy"; b.classList.remove("done"); }}, 1200);
}});
</script></body></html>"""


def list_items() -> list[dict]:
    out = []
    for name, path in sheet_files().items():
        s = parse(path)
        out.append({"name": name, "title": s["title"], "color": safe_color(s["color"]), "blurb": s.get("blurb", ""),
                    "count": s["count"], "sections": [x["name"] for x in s["sections"]], "user": s["user"]})
    return out


TEMPLATE = """---
title: {title}
color: "#0aa5b8"
blurb: My {title} commands.
---
## Basics
- `command --help` : what it does
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Open a cheatsheet from your cheatbook.")
    ap.add_argument("sheet", nargs="?", help="sheet name, e.g. git")
    ap.add_argument("--list-json", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--html", metavar="NAME", help=argparse.SUPPRESS)
    ap.add_argument("--new", metavar="NAME", help="create a new sheet of your own to fill in")
    ap.add_argument("--out", help=argparse.SUPPRESS)
    ap.add_argument("--events", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if a.list_json:
        print(json.dumps(list_items()))
    elif a.html:
        print(render(a.html))
    elif a.new:
        if not NAME_RE.match(a.new):
            raise SystemExit("Use letters, numbers, - and _ only.")
        USER.mkdir(parents=True, exist_ok=True)
        f = USER / f"{a.new}.md"
        if f.exists():
            raise SystemExit(f"{f} already exists.")
        f.write_text(TEMPLATE.format(title=a.new.replace("-", " ").title()), encoding="utf-8")
        print(f"Created {f} — add your commands, then reopen MyCheats.")
    elif a.sheet:
        out = DATA / "mycheats" / f"{a.sheet}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(a.sheet), encoding="utf-8")
        webbrowser.open(out.as_uri())
        print(f"Opened {out}")
    else:
        for it in list_items():
            print(f"  {it['name']:<16} {it['title']} ({it['count']} commands){'  [yours]' if it['user'] else ''}")
        print("\nOpen one:  run_tool mycheats <name>     New sheet:  run_tool mycheats --new <name>")


if __name__ == "__main__":
    main()
