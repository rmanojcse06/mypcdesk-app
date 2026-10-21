# Installing MyDesk on your PC

Three ways to install; all give the same app. Pick one:

| Way | Best for | Python needed |
| --- | --- | --- |
| [A. Download the app](#a-download-the-app) | Most people | No |
| [B. `pipx` command](#b-install-the-mydesk-command-with-pipx) | People who already use Python | 3.10-3.13 |
| [C. From source](#c-from-source) | Developing MyDesk or adding tools | 3.10-3.13 |

Then do the [first-run checks](#after-installing-first-run-checks). Upgrading, downgrading and removing are at the end.

**Requirements:** Windows 10/11, macOS 12+ or a recent Linux desktop; about 200 MB of memory while running; 150-200 MB of disk (plus about 300 MB if you add Clip Maker's video and OCR packages).

---

## A. Download the app

Go to **[Releases](https://github.com/rmanojcse06/mypcdesk-app/releases)** and open the newest version.

### Windows

1. Download **`MyDesk-Setup-<version>.exe`**.
2. Run it. Windows may say *"Windows protected your PC"* because this beta isn't code-signed yet: click **More info → Run anyway**.
3. Tick **Start MyDesk when I sign in** if you want it always running, then **Install**.
4. MyDesk opens. It's in the Start menu and on the desktop.

Portable instead: download **`MyDesk-<version>-windows.zip`**, unzip anywhere and run **`MyDesk.exe`**. Turn on sign-in start with `MyDesk-tool.exe autostart on`.

The window uses Microsoft Edge WebView2, which is built into Windows 11. On Windows 10 it comes with Edge; if it's missing, MyDesk opens in an Edge app window instead.

### macOS

1. Download **`MyDesk-<version>-macos.zip`** and unzip it.
2. Drag **MyDesk.app** to **Applications**.
3. First open: **right-click → Open → Open** (the beta isn't notarized yet). After that it opens normally.
4. Sign-in start: in Terminal, `/Applications/MyDesk.app/Contents/MacOS/MyDesk-tool autostart on`.

### Linux

```bash
tar xzf MyDesk-<version>-linux.tar.gz
./MyDesk/install.sh            # copies to ~/.local/opt/MyDesk, adds a menu entry, a `mydesk` command and login start
mydesk                         # open it
```

`./MyDesk/install.sh --no-startup` skips login start. A desktop with a system tray shows the tray icon; otherwise use the menu entry to bring MyDesk back.

---

## B. Install the `mydesk` command with pipx

1. Install [pipx](https://pipx.pypa.io/stable/installation/) if you don't have it:

   ```bash
   python -m pip install --user pipx
   python -m pipx ensurepath        # then open a new terminal
   ```

2. Install MyDesk from the release wheel:

   ```bash
   pipx install "mydesk[clip] @ https://github.com/rmanojcse06/mypcdesk-app/releases/download/v1.0.0-beta.2/mydesk-1.0.0b2-py3-none-any.whl"
   ```

   - Leave out `[clip]` to skip Clip Maker's video and OCR packages (about 300 MB).
   - On Linux, use `[clip,qt]` (or `[all]`) for a built-in window; without it MyDesk opens in a Chrome/Edge app window.
   - While the repo is private, the URL needs sign-in: download the `.whl` from Releases and run `pipx install "mydesk[clip] @ ./mydesk-1.0.0b2-py3-none-any.whl"`.

3. Start it and turn on sign-in start:

   ```bash
   mydesk                   # open MyDesk
   mydesk autostart on      # start at sign-in (Windows, macOS, Linux)
   ```

---

## C. From source

### Windows

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH** (Anaconda's Python 3.10-3.13 also works). Check in PowerShell: `py --version`.
2. Get the code, into any folder you like:

   ```powershell
   git clone https://github.com/rmanojcse06/mypcdesk-app.git
   cd mypcdesk-app
   ```

   No git? Use **Code → Download ZIP** on GitHub and unzip it.
3. Double-click **`install.bat`** (or `install.bat -NoStartup` to skip sign-in start). It:
   - finds Python 3.10-3.13
   - creates a private environment in `.venv`
   - installs the packages from `requirements.txt` (5-10 minutes the first time)
   - adds Desktop, Start-menu and sign-in shortcuts
   - checks for WebView2, then opens MyDesk

   If Windows asks whether to run the script, choose **More info → Run anyway**.
4. Later, start it with the **MyDesk** shortcut or `MyDesk.bat`.

### macOS and Linux

```bash
git clone https://github.com/rmanojcse06/mypcdesk-app.git
cd mypcdesk-app
./install.sh                 # or ./install.sh --no-startup
./mydesk.sh                  # start it later
```

On Linux install your distro's `python3-venv` package first if `venv` is missing (for example `sudo apt install python3-venv`).

In a source checkout, settings and data stay in the repo folder (`config.json`, `data/`), and `python mydesk.py <command>` works like `mydesk <command>`.

---

## After installing: first-run checks

1. **Header** shows your name and **BETA 2**. `mydesk version` prints `1.0.0-beta.2`.
2. **Health strip** shows CPU, memory and every drive. Press Caps Lock: its light changes within 2 seconds. Plug in a USB stick: a pop-up names it.
3. **Close button** minimizes MyDesk; it keeps running. Launching it again brings the same window back (only one copy ever runs). To end it, use Task Manager (or `"tray_quit": true` in settings for a tray Quit item).
4. **Heartbeat:** `mydesk status` (or `.venv\Scripts\python pc_status.py` in a source checkout) prints **ON**.
5. **A tool:** open **Junkyard → Clip Maker**, paste a YouTube Shorts link and press **Save clip**. Or `mydesk run clip_saver <link>` in a terminal.
6. **MyCheats:** **My Chest → MyCheats → Git** opens a cheatsheet window; the title bar counts it.
7. **Where things are:** `mydesk paths`.

| | Downloaded app or pipx | Source checkout |
| --- | --- | --- |
| Settings `config.json` | Windows `%APPDATA%\MyDesk` · macOS `~/Library/Application Support/MyDesk` · Linux `~/.local/share/mydesk` | the repo folder |
| Data (clips, events, status) | `data/` in that folder | `data/` in the repo |
| Your own tools | `tools/` in that folder | `mydesk/tools/` |

Set `MYDESK_HOME` to move everything somewhere else.

---

## Settings (optional)

Copy `config.example.json` to `config.json` in your settings folder and edit:

| Key | What it does | Default |
| --- | --- | --- |
| `name` | Name in the header | your OS username |
| `close_button` | `minimize` or `tray` | `minimize` |
| `keep_awake` | `claude-running`, `claude-busy` or `off` (only ever on the charger) | `claude-running` |
| `heartbeat_url` | Outgoing check-in every 5 min for a phone alert when the PC goes off (e.g. a free healthchecks.io check) | off |
| `whatsapp` | Relay URL and key for WhatsApp commands | off |

Restart MyDesk after editing.

**Claude box:** typing there always searches your tools. To also get answers from Claude, set an [Anthropic API key](https://console.anthropic.com/) and restart:

```powershell
setx ANTHROPIC_API_KEY "sk-ant-..."        # Windows
```

```bash
export ANTHROPIC_API_KEY="sk-ant-..."      # macOS / Linux, e.g. in ~/.zshrc
```

**Use MyDesk from your phone through Claude:** connect the MyDesk settings folder (or the repo folder) in the Claude desktop app. From the Claude app on your phone you can then ask "is my PC on?" or "save this reel with MyDesk".

**WhatsApp (optional):** about 20 minutes with a free Meta developer account and a free Cloudflare account. Follow [`relay/README.md`](../relay/README.md).

---

## Upgrade

1. Back up first: `mydesk backup` (zips settings and data, skips videos, keeps the last 5).
2. Then:
   - **Downloaded app:** run the newer installer over the old one, or unzip the new portable folder in place. Your settings and data are in a separate folder and are kept.
   - **pipx:** `pipx install --force "mydesk[clip] @ <new wheel URL>"`
   - **Source:** `git fetch --tags`, `git checkout v<new version>`, then run `install.bat` / `./install.sh` again to update packages.

## Downgrade

Install the older version the same way (older installer, older wheel, or `git checkout v<older version>` + install script). If the older version can't read newer data, restore the backup taken before the upgrade from `backups/`.

## Uninstall

- **Windows installer:** Settings → Apps → MyDesk → Uninstall. **Portable:** run `MyDesk-tool.exe autostart off`, then delete the folder.
- **macOS:** `MyDesk-tool autostart off`, then drag MyDesk.app to the Bin.
- **Linux tarball:** `mydesk autostart off`, then delete `~/.local/opt/MyDesk`, `~/.local/bin/mydesk` and `~/.local/share/applications/mydesk.desktop`.
- **pipx:** `mydesk autostart off`, then `pipx uninstall mydesk`.
- **Source:** `remove_startup.bat` (Windows) or `python mydesk.py autostart off`, delete the desktop/Start-menu shortcuts, then the folder.

Your settings and data folder is left in place; delete it yourself if you don't want to keep it.

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| "Python 3.10 - 3.13 not found" | Install Python 3.12 from python.org with **Add to PATH**, then run `install.bat` again |
| Package install fails behind a proxy or VPN | Retry on another network, or `set HTTPS_PROXY=...` before running the installer |
| Window opens in Edge/Chrome instead of its own window | WebView2 (Windows) or Qt (Linux) is missing; install WebView2 Runtime from Microsoft, or `pipx inject mydesk "mydesk[qt]"` on Linux. Everything still works |
| Nothing happens when I start MyDesk | It's already running, minimized or in the tray. Check the tray, or end `MyDesk`/`pythonw` in Task Manager and start again |
| `mydesk status` says OFF while it's open | The status file is in a different folder from the one you're checking; run `mydesk paths` in both places |
| Clip Maker: "login required" for Instagram/Facebook | Choose your browser under **Use my login from** (Firefox works best; close Chrome/Edge first) |
| Clip Maker downloads broke after working | Sites change; update yt-dlp: `.venv\Scripts\python -m pip install -U yt-dlp` (source) or `pipx upgrade mydesk --pip-args="-U yt-dlp"` |
| PC still sleeps while Claude runs | Stay-awake only works on the charger; check the health strip's awake chip. Closing the lid still sleeps unless Windows' lid action is "Do nothing" on AC |
| Copied the folder and git shows every file changed | `git config core.filemode false` |

Still stuck? Open an issue on [GitHub](https://github.com/rmanojcse06/mypcdesk-app/issues) with the output of `mydesk version` and `mydesk paths`.
