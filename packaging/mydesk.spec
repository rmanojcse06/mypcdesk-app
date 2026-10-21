# PyInstaller recipe for MyDesk (Windows).  Build:  pyinstaller packaging/mydesk.spec --noconfirm
# Produces dist/MyDesk/ with two programs that share one bundled Python:
#   MyDesk.exe       the app (no console window)
#   MyDesk-tool.exe  runs tool scripts for MyDesk (console program, started hidden) so their progress can be read
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 (SPECPATH is set by PyInstaller)

datas = [
    (os.path.join(ROOT, "ui"), "ui"),
    (os.path.join(ROOT, "tools"), "tools"),
    (os.path.join(ROOT, "sections.json"), "."),
    (os.path.join(ROOT, "VERSION"), "."),
    (os.path.join(ROOT, "config.example.json"), "."),
    (os.path.join(ROOT, "pc_status.py"), "."),
    (os.path.join(ROOT, "remote"), "remote"),
]
binaries, hiddenimports = [], ["core", "core.server", "core.whatsapp", "core.keepawake"]

# Packages the tool scripts import at run time (PyInstaller can't see those imports on its own).
for pkg in ["webview", "pystray", "psutil", "markdown", "PIL", "yt_dlp", "imageio_ffmpeg",
            "rapidocr", "onnxruntime", "cv2", "numpy", "pycaw", "comtypes"]:
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue  # optional on this platform
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

icon = os.path.join(ROOT, "ui", "mydesk.ico")
app = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MyDesk", console=False, icon=icon)  # noqa: F821
tool = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MyDesk-tool", console=True, icon=icon)  # noqa: F821
COLLECT(app, tool, a.binaries, a.datas, name="MyDesk")  # noqa: F821
