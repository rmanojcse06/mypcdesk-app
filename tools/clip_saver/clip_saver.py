#!/usr/bin/env python
"""Clip Maker — save a reel or video with its caption, screenshots and on-screen text.

Works with YouTube, Instagram, Facebook, LinkedIn, X and the ~1800 other sites
yt-dlp supports. For each link it:

  1. downloads the video with yt-dlp (open-source CLI downloader)
  2. grabs screenshots from the video (start, middle, end) with ffmpeg
  3. reads any text in those screenshots with OCR (RapidOCR, or Tesseract if installed)
  4. collects the description / caption, author, date, tags and counts
  5. writes everything to clip.md (Markdown) + clip.html in its own folder

Run on its own:
    python clip_saver.py "https://www.youtube.com/shorts/XXXX"
    python clip_saver.py URL --cookies-from-browser firefox   # for Instagram/Facebook logins
    python clip_saver.py URL --no-video                       # keep only thumbnail + text
Saved under:  <out>/clips/<YYYY-MM-DD>/<Platform>-<id>/
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent.parent / "data" / "clip_saver"
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
EVENTS = False


# ---------------------------------------------------------------- reporting
def say(msg: str, level: str = "info") -> None:
    if EVENTS:
        print("@@" + json.dumps({"event": "progress", "msg": msg, "level": level}), flush=True)
    else:
        print(("! " if level == "warn" else "• ") + msg, flush=True)


def finish(result: dict) -> None:
    if EVENTS:
        print("@@" + json.dumps({"event": "result", **result}), flush=True)
    else:
        print(f"\nSaved: {result['md_file']}")


def fail(msg: str) -> None:
    if EVENTS:
        print("@@" + json.dumps({"event": "error", "msg": msg}), flush=True)
    else:
        print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- helpers
def ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg  # bundled ffmpeg binary, no separate install

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def run_ffmpeg(args: list[str]) -> bool:
    exe = ffmpeg_exe()
    if not exe:
        return False
    proc = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y", *args],
                          capture_output=True, creationflags=CREATE_NO_WINDOW)
    return proc.returncode == 0


def clock(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def md_escape(text: str) -> str:
    """Make caption text safe to drop into Markdown: no raw HTML from the internet."""
    return html.escape(text or "", quote=False)


def yaml_str(value) -> str:
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------- steps
def download(url: str, out_dir: Path, no_video: bool, cookies_browser: str | None, cookies_file: str | None) -> tuple[dict, Path]:
    try:
        import yt_dlp
    except ImportError:
        fail("yt-dlp is not installed. Run: pip install yt-dlp")

    day = dt.date.today().isoformat()
    template = str(out_dir / "clips" / day / "%(extractor_key)s-%(id)s" / "%(_fname)s")
    opts = {
        "quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True,
        "outtmpl": {"default": template.replace("%(_fname)s", "video.%(ext)s"),
                    "thumbnail": template.replace("%(_fname)s", "thumbnail.%(ext)s")},
        "format": "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4]/bv*[height<=1080]+ba/b",
        "merge_output_format": "mp4",
        "writethumbnail": True,
        "skip_download": no_video,
        "restrictfilenames": True,
        "windowsfilenames": True,
    }
    ff = ffmpeg_exe()
    if ff:
        opts["ffmpeg_location"] = ff
    if cookies_browser:
        opts["cookiesfrombrowser"] = (cookies_browser,)
    if cookies_file:
        opts["cookiefile"] = cookies_file

    say("Reading the link" + (" (video download skipped)" if no_video else " and downloading the video"))
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get("_type") == "playlist" and info.get("entries"):
                info = next(e for e in info["entries"] if e)
            folder = Path(ydl.prepare_filename(info, outtmpl=opts["outtmpl"]["default"])).parent
    except Exception as exc:  # yt_dlp.utils.DownloadError and friends
        msg = re.sub(r"\x1b\[[0-9;]*m", "", str(exc)).replace("ERROR: ", "")
        hint = ""
        if re.search(r"login|log in|cookies|private|rate-limit|not available", msg, re.I):
            hint = " Tip: this site needs you signed in. Pick a browser under 'Use my login from' (Firefox works best)."
        fail(msg[:400] + hint)
    folder.mkdir(parents=True, exist_ok=True)
    return info, folder


def find_video(info: dict, folder: Path) -> Path | None:
    for d in info.get("requested_downloads") or []:
        p = Path(d.get("filepath") or "")
        if p.is_file():
            return p
    hits = [p for p in folder.glob("video.*") if p.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov")]
    return hits[0] if hits else None


def make_screenshots(video: Path | None, folder: Path, duration: float | None, count: int) -> list[tuple[Path, float | None]]:
    shots: list[tuple[Path, float | None]] = []
    if video and ffmpeg_exe():
        dur = duration or 0
        if dur > 3 and count > 1:
            marks = [dur * f for f in ([0.1, 0.5, 0.9] if count == 3 else [i / (count + 1) for i in range(1, count + 1)])]
        else:
            marks = [min(1.0, dur / 2) if dur else 1.0]
        for i, t in enumerate(marks, 1):
            target = folder / f"shot_{i}.png"
            if run_ffmpeg(["-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(target)]) and target.exists():
                shots.append((target, t))
    if not shots:  # fall back to the thumbnail
        thumbs = sorted(folder.glob("thumbnail.*"))
        if thumbs:
            target = folder / "shot_1.png"
            if thumbs[0].suffix.lower() == ".png":
                shutil.copy(thumbs[0], target)
            elif not run_ffmpeg(["-i", str(thumbs[0]), str(target)]):
                target = thumbs[0]
            shots.append((target, None))
    return shots


_ocr_engine = None


def ocr_image(path: Path) -> str | None:
    """Returns text found in the image, '' if none, None if no OCR engine is available."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = False
        try:
            from rapidocr import RapidOCR  # rapidocr >= 2

            _ocr_engine = ("rapidocr2", RapidOCR())
        except Exception:
            try:
                from rapidocr_onnxruntime import RapidOCR  # older package name

                _ocr_engine = ("rapidocr1", RapidOCR())
            except Exception:
                try:
                    import pytesseract

                    pytesseract.get_tesseract_version()
                    _ocr_engine = ("tesseract", pytesseract)
                except Exception:
                    _ocr_engine = False
    if not _ocr_engine:
        return None
    kind, engine = _ocr_engine
    try:
        if kind == "rapidocr2":
            out = engine(str(path))
            lines = list(getattr(out, "txts", None) or [])
        elif kind == "rapidocr1":
            result, _ = engine(str(path))
            lines = [r[1] for r in (result or [])]
        else:
            from PIL import Image

            lines = engine.image_to_string(Image.open(path)).splitlines()
    except Exception as exc:
        say(f"OCR failed on {path.name}: {exc}", "warn")
        return ""
    return "\n".join(line.strip() for line in lines if line and line.strip())


# ---------------------------------------------------------------- note writing
def build_markdown(info: dict, url: str, video: Path | None, shots: list, ocr: list) -> tuple[str, dict]:
    platform = info.get("extractor_key") or info.get("extractor") or "Web"
    platform = {"Youtube": "YouTube", "YoutubeTab": "YouTube", "Linkedin": "LinkedIn", "Tiktok": "TikTok", "Twitter": "X"}.get(platform, platform)
    author = info.get("uploader") or info.get("channel") or info.get("creator") or ""
    title = (info.get("title") or "").strip() or f"{platform} clip"
    description = (info.get("description") or "").strip()
    uploaded = info.get("upload_date") or ""
    if re.fullmatch(r"\d{8}", uploaded):
        uploaded = f"{uploaded[:4]}-{uploaded[4:6]}-{uploaded[6:]}"
    captured = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    tags = [str(t) for t in (info.get("tags") or [])][:20]
    cover = shots[0][0].name if shots else None

    meta = {
        "title": title, "platform": platform, "url": info.get("webpage_url") or url, "author": author,
        "author_url": info.get("uploader_url") or info.get("channel_url") or "",
        "uploaded": uploaded, "captured": captured, "duration": info.get("duration"),
        "tags": tags, "video": video.name if video else None, "cover": cover,
    }
    fm = "\n".join(f"{k}: {yaml_str(v)}" for k, v in meta.items())

    lines = [f"---\n{fm}\n---", "", f"# {md_escape(title)}", ""]
    by = f"[{md_escape(author)}]({meta['author_url']})" if author and meta["author_url"] else md_escape(author)
    lines.append(" · ".join(x for x in [f"**{platform}**", by, f"uploaded {uploaded}" if uploaded else "", f"[open original]({meta['url']})"] if x))
    lines.append("")
    if shots:
        lines += [" ".join(f"![{'Frame at ' + clock(t) if t is not None else 'Thumbnail'}]({p.name})" for p, t in shots), ""]

    lines += ["## Caption / description", ""]
    if description:
        lines += ["> " + (line if line.strip() else "") for line in md_escape(description).splitlines()]
    else:
        lines.append("_No caption or description on this post._")
    lines.append("")

    lines += ["## Text seen in the video (OCR)", ""]
    if all(o is None for o in ocr):
        lines.append("_OCR engine not installed — run `pip install rapidocr onnxruntime`._")
    elif not any(ocr):
        lines.append("_No readable text in the screenshots._")
    else:
        for (p, t), text in zip(shots, ocr):
            if text:
                label = f"Frame at {clock(t)}" if t is not None else "Thumbnail"
                lines += [f"**{label}**", "", "```text", text.replace("```", "'''"), "```", ""]
    lines.append("")

    details = [("Duration", clock(info["duration"]) if info.get("duration") else None),
               ("Views", f"{info['view_count']:,}" if info.get("view_count") else None),
               ("Likes", f"{info['like_count']:,}" if info.get("like_count") else None),
               ("Comments", f"{info['comment_count']:,}" if info.get("comment_count") else None),
               ("Tags", ", ".join(md_escape(t) for t in tags) if tags else None),
               ("Video file", video.name if video else "not saved"),
               ("Saved", captured)]
    lines += ["## Details", "", "| | |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in details if v]
    lines.append("")
    return "\n".join(lines), meta


def write_html(md_text: str, meta: dict, folder: Path) -> None:
    try:
        import markdown
    except ImportError:
        return
    body = markdown.markdown(re.sub(r"^---\n.*?\n---\n", "", md_text, flags=re.S), extensions=["fenced_code", "tables"])
    video = f'<video controls src="{html.escape(meta["video"])}"></video>' if meta.get("video") else ""
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(meta['title'])}</title>
<style>body{{font:15px/1.6 "Segoe UI",system-ui,sans-serif;color:#1d2233;background:#fbf6ec;margin:0}}
main{{max-width:900px;margin:30px auto;background:#fff;border:2px solid #1d2233;border-radius:14px;box-shadow:4px 4px 0 #1d2233;padding:26px 32px}}
h1,h2{{font-family:Cambria,Georgia,serif}} h2{{border-bottom:2px solid #1d2233;padding-bottom:4px}}
img{{max-width:31%;border:2px solid #1d2233;border-radius:10px;margin:0 1% 8px 0;vertical-align:top}}
video{{width:100%;max-height:480px;background:#000;border-radius:10px}}
blockquote{{margin:0;padding:10px 16px;background:#fbf6ec;border-left:5px solid #e5484d}}
pre{{background:#f3efe5;padding:12px;border-radius:10px;white-space:pre-wrap}}
td,th{{border:1px solid #ddd5c4;padding:5px 10px}} table{{border-collapse:collapse}}</style></head>
<body><main>{video}{body}</main></body></html>"""
    (folder / "clip.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- main
def main() -> None:
    global EVENTS
    ap = argparse.ArgumentParser(description="Save a reel/video with caption, screenshots and OCR text as Markdown.")
    ap.add_argument("url", help="link to the reel, short or video")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="data folder (default: MyDesk/data/clip_saver)")
    ap.add_argument("--cookies-from-browser", default="", help="use your login from: firefox, edge, chrome, brave")
    ap.add_argument("--cookies", default="", help="path to a cookies.txt file (alternative to a browser)")
    ap.add_argument("--no-video", action="store_true", help="don't keep the video file, only thumbnail + text")
    ap.add_argument("--shots", type=int, default=3, help="number of screenshots to take (default 3)")
    ap.add_argument("--no-ocr", action="store_true", help="skip reading text from screenshots")
    ap.add_argument("--events", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    EVENTS = a.events

    url = a.url.strip()
    if not re.match(r"^https?://", url):
        fail("Please paste a full link starting with http:// or https://")
    out_dir = Path(a.out)

    info, folder = download(url, out_dir, a.no_video, a.cookies_from_browser or None, a.cookies or None)
    say(f"Found: {info.get('title') or 'untitled'} — {info.get('uploader') or info.get('extractor_key')}")
    video = None if a.no_video else find_video(info, folder)
    if not a.no_video and not video:
        say("No video file came back (image post?) — using the thumbnail", "warn")

    say("Taking screenshots")
    shots = make_screenshots(video, folder, info.get("duration"), max(1, min(a.shots, 6)))
    if not shots:
        say("Couldn't capture a screenshot (ffmpeg missing?)", "warn")

    ocr: list = []
    if shots and not a.no_ocr:
        say("Reading text in the screenshots (OCR)")
        ocr = [ocr_image(p) for p, _ in shots]
        if ocr and all(o is None for o in ocr):
            say("No OCR engine found — install with: pip install rapidocr onnxruntime", "warn")
    else:
        ocr = [None] * len(shots)

    say("Writing the Markdown note")
    md_text, meta = build_markdown(info, url, video, shots, ocr)
    md_file = folder / "clip.md"
    md_file.write_text(md_text, encoding="utf-8")
    (folder / "info.json").write_text(json.dumps({k: info.get(k) for k in (
        "id", "title", "description", "uploader", "uploader_url", "channel", "upload_date", "duration",
        "view_count", "like_count", "comment_count", "tags", "webpage_url", "extractor_key")}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_html(md_text, meta, folder)

    rel = md_file.relative_to(out_dir).as_posix()
    finish({"msg": f"Saved “{meta['title'][:60]}”", "md_file": str(md_file), "open": rel})


if __name__ == "__main__":
    main()
