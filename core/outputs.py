"""Lists and renders the Markdown notes tools save (e.g. Clip Maker's clip.md)."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

import markdown

from .config import DATA_DIR, tool_data_dir

FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def parse_front_matter(text: str) -> tuple[dict, str]:
    m = FRONT_MATTER.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        raw = raw.strip()
        try:
            meta[key.strip()] = json.loads(raw) if raw[:1] in '"[{' or raw in ("true", "false", "null") or re.fullmatch(r"-?\d+(\.\d+)?", raw) else raw
        except json.JSONDecodeError:
            meta[key.strip()] = raw
    return meta, text[m.end():]


def safe_path(tool_id: str, rel: str) -> Path:
    base = tool_data_dir(tool_id).resolve()
    target = (base / rel).resolve()
    if base != target and base not in target.parents:
        raise PermissionError("path outside tool data folder")
    return target


def list_outputs(tool: dict) -> list[dict]:
    spec = tool.get("outputs") or {}
    pattern = spec.get("glob", "**/*.md")
    base = tool_data_dir(tool["id"])
    items = []
    for md in base.glob(pattern):
        try:
            meta, _ = parse_front_matter(md.read_text(encoding="utf-8"))
        except OSError:
            continue
        rel = md.relative_to(base).as_posix()
        thumb = meta.get("cover")
        items.append({
            "path": rel,
            "title": meta.get("title") or md.parent.name,
            "platform": meta.get("platform", ""),
            "author": meta.get("author", ""),
            "captured": meta.get("captured", ""),
            "cover": f"{md.parent.relative_to(base).as_posix()}/{thumb}" if thumb else None,
            "mtime": md.stat().st_mtime,
        })
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


def render_output(tool: dict, rel: str, files_url: str) -> dict:
    """Markdown -> HTML. Relative image/video links point at the /files endpoint."""
    md_path = safe_path(tool["id"], rel)
    meta, body = parse_front_matter(md_path.read_text(encoding="utf-8"))
    folder = md_path.parent.relative_to(tool_data_dir(tool["id"]).resolve()).as_posix()
    html_body = markdown.markdown(body, extensions=["fenced_code", "tables"])

    def fix(m: re.Match) -> str:
        attr, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|data:|#|/)", url):
            return m.group(0)
        return f'{attr}="{files_url(tool["id"], f"{folder}/{url}")}"'

    html_body = re.sub(r'(src|href)="([^"]+)"', fix, html_body)
    video = meta.get("video")
    video_url = files_url(tool["id"], f"{folder}/{video}") if video else None
    return {"meta": meta, "html": html_body, "video_url": video_url}


def files_url_factory(token: str):
    def files_url(tool_id: str, rel: str) -> str:
        return f"/files/{quote(tool_id)}/{quote(rel)}?t={quote(token)}"
    return files_url
