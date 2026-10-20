"""Device indicators for the health strip: drives, USB devices, audio jack,
touchscreen and Caps / Num / Scroll Lock.

Fast checks (lock keys, drives) run on every request. Slow checks (USB device
list, audio endpoints) run in a background thread every few seconds and are
cached. Anything a platform can't report comes back as None and the UI hides it.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import threading
import time

import psutil

IS_WIN = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0

_lock = threading.Lock()
_cache: dict = {"usb": None, "audio": None}


# ---------------------------------------------------------------- lock keys
def lock_keys() -> dict | None:
    if IS_WIN:
        try:
            import ctypes

            gks = ctypes.windll.user32.GetKeyState
            return {"caps": bool(gks(0x14) & 1), "num": bool(gks(0x90) & 1), "scroll": bool(gks(0x91) & 1)}
        except Exception:
            return None
    # Linux: keyboard LEDs are exposed in sysfs
    out = {}
    for key, pattern in (("caps", "*capslock"), ("num", "*numlock"), ("scroll", "*scrolllock")):
        leds = glob.glob(f"/sys/class/leds/{pattern}/brightness")
        if leds:
            try:
                out[key] = any(open(p).read().strip() not in ("", "0") for p in leds)
            except OSError:
                pass
    return out or None


# ---------------------------------------------------------------- touchscreen
def touchscreen() -> dict | None:
    if IS_WIN:
        try:
            import ctypes

            gsm = ctypes.windll.user32.GetSystemMetrics
            digitizer = gsm(94)          # SM_DIGITIZER
            points = gsm(95)             # SM_MAXIMUMTOUCHES
            has_touch = bool(digitizer & 0x03)   # integrated or external touch
            return {"present": has_touch, "ready": bool(digitizer & 0x80), "points": points,
                    "pen": bool(digitizer & 0x0C)}
        except Exception:
            return None
    try:
        names = open("/proc/bus/input/devices").read().lower()
        return {"present": "touchscreen" in names or "touch screen" in names, "ready": True, "points": 0, "pen": "stylus" in names}
    except OSError:
        return None


# ---------------------------------------------------------------- drives
def _volume_label(mount: str) -> str:
    if not IS_WIN:
        return ""
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(261)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(ctypes.c_wchar_p(mount), buf, 261, None, None, None, None, 0)
        return buf.value if ok else ""
    except Exception:
        return ""


def drives() -> list[dict]:
    out = []
    try:
        parts = psutil.disk_partitions(all=False)
    except Exception:
        return out
    for p in parts:
        opts = p.opts or ""
        if "cdrom" in opts or not p.fstype:
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except (PermissionError, OSError):
            continue
        if u.total < 2**30 and "removable" not in opts:  # skip tiny virtual mounts
            continue
        removable = "removable" in opts or p.mountpoint.startswith(("/media/", "/run/media/", "/Volumes/"))
        kind = "usb" if removable else ("network" if "remote" in opts else "fixed")
        name = p.mountpoint.rstrip("\\") if IS_WIN else p.mountpoint
        out.append({"mount": p.mountpoint, "name": name, "label": _volume_label(p.mountpoint), "kind": kind,
                    "fs": p.fstype, "percent": round(u.percent),
                    "free_gb": round(u.free / 2**30, 1), "total_gb": round(u.total / 2**30, 1)})
    out.sort(key=lambda d: (d["kind"] != "fixed", d["name"]))
    return out


# ---------------------------------------------------------------- USB devices (slow, cached)
_USB_PS = (
    "Get-CimInstance Win32_PnPEntity | "
    "Where-Object { $_.PNPDeviceID -like 'USB\\VID*' -and $_.PNPClass -ne 'USB' -and $_.Name } | "
    "Select-Object Name, PNPClass | ConvertTo-Json -Compress"
)


def _usb_devices() -> list[dict] | None:
    if IS_WIN:
        try:
            proc = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _USB_PS],
                                  capture_output=True, text=True, timeout=20, creationflags=CREATE_NO_WINDOW)
            raw = proc.stdout.strip()
            if not raw:
                return []
            data = json.loads(raw)
            data = data if isinstance(data, list) else [data]
        except Exception:
            return None
        seen, out = set(), []
        for d in data:
            name = (d.get("Name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            out.append({"name": name, "kind": _usb_kind(d.get("PNPClass") or "", name)})
        return out
    # Linux: product names from sysfs, skipping hubs
    out = []
    for dev in glob.glob("/sys/bus/usb/devices/*"):
        try:
            if open(os.path.join(dev, "bDeviceClass")).read().strip() == "09":
                continue
            name = open(os.path.join(dev, "product")).read().strip()
        except OSError:
            continue
        out.append({"name": name, "kind": _usb_kind("", name)})
    return out if glob.glob("/sys/bus/usb/devices") else None


def _usb_kind(pnp_class: str, name: str) -> str:
    c, n = pnp_class.lower(), name.lower()
    if c in ("diskdrive", "volume") or "storage" in n or "disk" in n:
        return "storage"
    if "keyboard" in n or c == "keyboard":
        return "keyboard"
    if "mouse" in n or c == "mouse":
        return "mouse"
    if c in ("wpd",) or "phone" in n or "android" in n or "iphone" in n:
        return "phone"
    if c in ("media", "audioendpoint") or "audio" in n or "headset" in n:
        return "audio"
    if c in ("camera", "image") or "camera" in n or "webcam" in n:
        return "camera"
    if c == "bluetooth" or "bluetooth" in n:
        return "bluetooth"
    if c == "hidclass" or "hid" in n:
        return "input"
    return "other"


# ---------------------------------------------------------------- audio endpoints (slow, cached)
_JACK_WORDS = ("headphone", "headset", "earphone", "earbud", "line out", "lineout")


def _audio() -> dict | None:
    if not IS_WIN:
        return None
    try:
        import comtypes
        from pycaw.pycaw import AudioUtilities
    except Exception:
        return None
    try:
        comtypes.CoInitialize()
    except Exception:
        pass
    try:
        outputs, unplugged = [], []
        for d in AudioUtilities.GetAllDevices():
            dev_id = str(getattr(d, "id", "") or "")
            if not dev_id.startswith("{0.0.0."):  # render (output) endpoints only
                continue
            state = getattr(getattr(d, "state", None), "name", str(getattr(d, "state", "")))
            name = d.FriendlyName or "Audio output"
            if state == "Active":
                outputs.append(name)
            elif state == "Unplugged":
                unplugged.append(name)
        jack = any(any(w in n.lower() for w in _JACK_WORDS) for n in outputs)
        return {"outputs": outputs, "unplugged": unplugged, "jack": jack}
    except Exception:
        return None


def _poll_slow() -> None:
    while True:
        usb = _usb_devices()
        audio = _audio()
        with _lock:
            _cache["usb"] = usb
            _cache["audio"] = audio
        time.sleep(6)


def start_device_poller() -> None:
    threading.Thread(target=_poll_slow, name="device-poller", daemon=True).start()


def snapshot() -> dict:
    with _lock:
        usb = _cache["usb"]
        audio = _cache["audio"]
    return {"locks": lock_keys(), "touch": touchscreen(), "drives": drives(), "usb": usb, "audio": audio}
