# PyInstaller recipe for MyDesk — Windows, macOS and Linux.
#   pyinstaller packaging/mydesk.spec --noconfirm
# Produces dist/MyDesk/ with two programs sharing one bundled Python:
#   MyDesk       the app (no console window)
#   MyDesk-tool  the same program as a console app: runs tool scripts and the `mydesk` command line
# On macOS it also wraps the app as dist/MyDesk.app.
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 (SPECPATH is set by PyInstaller)
PKG = os.path.join(ROOT, "mydesk")

datas = [
    (os.path.join(PKG, "ui"), "mydesk/ui"),
    (os.path.join(PKG, "tools"), "mydesk/tools"),
    (os.path.join(PKG, "sections.json"), "mydesk"),
    (os.path.join(PKG, "VERSION"), "mydesk"),
    (os.path.join(PKG, "config.example.json"), "mydesk"),
]
binaries = []
hiddenimports = collect_submodules("mydesk")

# Packages the tool scripts import at run time (PyInstaller can't see those imports on its own).
for pkg in ["webview", "pystray", "psutil", "markdown", "PIL", "yt_dlp", "imageio_ffmpeg",
            "rapidocr", "onnxruntime", "cv2", "numpy", "pycaw", "comtypes"]:
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue  # not used on this platform
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "mydesk.py")],
    pathex=[ROOT],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "pytest"],
)
pyz = PYZ(a.pure)  # noqa: F821

icon = os.path.join(PKG, "ui", "mydesk.ico") if sys.platform == "win32" else None
app = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MyDesk", console=False, icon=icon)  # noqa: F821
tool = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MyDesk-tool", console=True, icon=icon)  # noqa: F821
coll = COLLECT(app, tool, a.binaries, a.datas, name="MyDesk")  # noqa: F821

if sys.platform == "darwin":
    BUNDLE(coll, name="MyDesk.app", bundle_identifier="com.mydesk.app",  # noqa: F821
           info_plist={"CFBundleShortVersionString": open(os.path.join(PKG, "VERSION")).read().strip(),
                       "NSHighResolutionCapable": True})
