# MyDesk 1.0.0-beta.1

First beta: everything below works today. The three-panel lobby is designed and prototyped and comes in a later beta.

## Install

- **Windows installer** (`MyDesk-Setup-1.0.0-beta.1.exe`): no Python needed. Windows may say "unknown publisher" because this beta isn't code-signed yet: choose **More info → Run anyway**.
- **Portable zip**: unzip anywhere and run `MyDesk.exe`.
- **From source**: download the code and double-click `install.bat` (needs Python 3.10–3.13).

Your settings and data live in `%APPDATA%\MyDesk` and are kept when you update or uninstall.

## What's in it

**The app**
- Colourful window that starts at sign-in and keeps running: the close button minimizes it, a tray icon reopens it, and a second launch brings back the running copy. End it in Task Manager.
- Eight sections with hover menus that stay tidy however many tools you add.
- Search box for every section and tool, and optional chat with Claude (needs an API key).

**Health**
- CPU, memory, storage, last reboot and sign-in.
- Every drive, with USB drives marked; USB devices; headphones or speakers; touchscreen; Caps, Num and Scroll Lock lights; pop-ups when something is plugged in or removed.
- OS Monitor: CPU per core, disks, network speed, busiest apps, and **Ports in use** (which app holds which port, and whether it's reachable from your network).

**Tools** (each one also runs from a terminal with `run_tool`)
- **Clip Maker:** saves a reel or video with its caption, screenshots and the text inside them (OCR), as a Markdown note.
- **MyCheats:** searchable Git, Windows CMD and PowerShell cheatsheets in their own windows; add your own sheets.
- Dialog counter in the title bar and header.

**Calendar and notifications**
- Birthdays, anniversaries, seminars and bills. Upcoming 15 days and earlier this month, acknowledged one occurrence at a time, so next year's birthday reminds you again.
- Bell for events due within 3 days and recent activity.

**Remote and power**
- **Stay awake while Claude works**, only while the charger is connected.
- **"Is my computer on?"**: a status file every 30 seconds and `pc_status.py`; optional check-in URL for phone alerts.
- **Use MyDesk from your phone through Claude:** a file mailbox with a fixed list of allowed actions; no ports opened.
- **WhatsApp** (official Cloud API, optional): `status`, `awake 2h`, `clip <link>`, `events`, `say …` through your own free relay. Setup in `relay/README.md`.

## Known limits in this beta

- The Windows-only parts (tray, device checks, stay-awake, separate dialog windows) are new and haven't had wide testing yet; please report anything odd.
- The USB check runs PowerShell every 6 seconds, which causes small CPU spikes; event-based detection is planned.
- The installer isn't signed yet.
- Clip Maker may need signing in through your browser for Instagram and Facebook links.
