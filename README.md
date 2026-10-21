# MyDesk

**A colourful personal desktop app that holds all your own tools in one place.** It starts with your computer, shows live system health, and groups tools into sections like Finance, Events, Social and Junkyard. Every tool is a plain Python script, so you can run it from the app or from a terminal.

![MyDesk home with the Junkyard menu open](docs/screenshots/home.png)

**Docs:** [Install guide](docs/INSTALL.md) · [Architecture and diagrams](docs/ARCHITECTURE.md) · [Plan and roadmap](docs/PLAN.md) · [Changelog](CHANGELOG.md) · [Add a tool](CONTRIBUTING.md)

- **Starts with Windows** (or macOS/Linux login) as its own window
- **Live health strip:** CPU, memory, storage, last reboot and sign-in
- **Eight sections** with hover menus that stay tidy however many tools you add (a filter box appears when a section has more than 8)
- **Every tool is a script:** add a folder with a `tool.json` and the app builds its form for you
- **Search + Claude box:** type to jump to any section or tool, or ask Claude if you set an API key
- **Local only:** the app runs on `127.0.0.1` with a per-launch access token. Nothing leaves your machine unless a tool fetches something.

## Included tools

### Clip Maker (Junkyard)

Paste a reel, short or video link from YouTube, Instagram, Facebook, LinkedIn, X or any of the ~1800 sites [yt-dlp](https://github.com/yt-dlp/yt-dlp) supports. Clip Maker:

1. downloads the video with **yt-dlp**
2. takes screenshots at the start, middle and end with **ffmpeg** (bundled, nothing to install)
3. reads the text in those frames with **OCR** ([RapidOCR](https://github.com/RapidAI/RapidOCR), with Tesseract as a fallback)
4. saves the caption / description, author, upload date, tags and counts
5. writes a Markdown note (`clip.md`) and an HTML copy, shown in MyDesk with the video player

| Save a clip | Saved note |
| --- | --- |
| ![Clip Maker form and library](docs/screenshots/clip-saver.png) | ![A saved clip rendered from Markdown](docs/screenshots/clip-note.png) |

Instagram and Facebook usually need you signed in. Pick your browser under **Use my login from**: Firefox works best, because Chrome and Edge lock their cookies while they're open.

> Saved videos are for your personal reference. They belong to their creators, and most platforms' terms don't allow re-uploading them.

### OS Monitor

Live per-core CPU, disks, network speed and the busiest apps, refreshed every 3 seconds.

![OS Monitor](docs/screenshots/os-monitor.png)

## Sections

| Section | For | Status |
| --- | --- | --- |
| OS Monitor | System health | Live monitor |
| My Finance | Investments, accounts, budget | Planned |
| My Events | Calendars, birthdays, reminders | Planned |
| My Social | Follows, posting, blog drafts | Planned |
| My Chest | Bills, spending, subscriptions | Planned |
| Junkyard | Your own experiments | Clip Maker |
| My Mirror | Photos and videos | Planned |
| My Block | Certificates and important documents | Planned |

Rename sections, change colours or list planned tools in [`sections.json`](sections.json).

## Install

**Current version: 1.0.0-beta.2** — see [CHANGELOG.md](CHANGELOG.md). Pick whichever suits you; all three give the same app. Step-by-step instructions, first-run checks, upgrade, uninstall and troubleshooting are in **[docs/INSTALL.md](docs/INSTALL.md)**.

### 1. Download an app (no Python needed)

From the repo's **Releases** page:

| System | Download | Then |
| --- | --- | --- |
| Windows | `MyDesk-Setup-<version>.exe` | Run it; tick "Start MyDesk when I sign in". Unsigned beta: **More info → Run anyway** |
| Windows (portable) | `MyDesk-<version>-windows.zip` | Unzip anywhere, run `MyDesk.exe` |
| macOS | `MyDesk-<version>-macos.zip` | Unzip, move **MyDesk.app** to Applications. First open: right-click → **Open** (unsigned beta) |
| Linux | `MyDesk-<version>-linux.tar.gz` | `tar xzf …` then `./MyDesk/install.sh` (adds a menu entry, a `mydesk` command and login start) |

### 2. Install the `mydesk` command (Python 3.10–3.13)

```bash
pipx install "mydesk[clip] @ https://github.com/rmanojcse06/mypcdesk-app/releases/download/v1.0.0-beta.2/mydesk-1.0.0b2-py3-none-any.whl"
mydesk autostart on        # start at sign-in (Windows, macOS and Linux)
mydesk                     # open MyDesk
```

Leave out `[clip]` to skip Clip Maker's video and OCR packages (about 300 MB). While the repo is private, download the `.whl` from Releases and run `pipx install "mydesk[clip] @ ./mydesk-….whl"`. On Linux add `[qt]` for a built-in window; otherwise MyDesk opens in a Chrome/Edge app window.

### 3. From source (for developing MyDesk)

**Windows:** clone the repo and double-click **`install.bat`** (`install.bat -NoStartup` to skip sign-in start). **macOS / Linux:** `./install.sh` (`--no-startup` to skip). Both create `.venv`, install packages, add shortcuts and open MyDesk; `python mydesk.py <command>` works like `mydesk <command>`.

### Where your things live

| | Downloaded app or `pipx` | Source checkout |
| --- | --- | --- |
| Settings `config.json` | Windows `%APPDATA%\MyDesk` · macOS `~/Library/Application Support/MyDesk` · Linux `~/.local/share/mydesk` | the repo folder |
| Data (clips, events, status) | `data/` in that same folder | `data/` in the repo |
| Your own tools | `tools/` in that same folder | `mydesk/tools/` |

Updating or uninstalling never touches these. `mydesk paths` prints them, `mydesk backup` zips settings and data, and `MYDESK_HOME` moves everything.

### Settings

Copy `config.example.json` to `config.json` in your settings folder to set your name (otherwise your OS username is used), the window, stay-awake mode and the optional WhatsApp bridge.

### Chat with Claude (optional)

Typing in the Claude box always searches your sections and tools. To ask Claude questions too, set an [Anthropic API key](https://console.anthropic.com/) and restart MyDesk:

```powershell
setx ANTHROPIC_API_KEY "sk-ant-..."      # Windows
```

```bash
export ANTHROPIC_API_KEY="sk-ant-..."    # macOS / Linux, e.g. in ~/.zshrc
```

## The `mydesk` command

```
mydesk                          open MyDesk (brings the running copy forward)
mydesk tools                    list tools
mydesk run clip_saver <link>    run a tool in the terminal (add --help for its options)
mydesk cheats [git]             open a cheatsheet; mydesk run mycheats --new docker for your own
mydesk status                   is this computer on? (MyDesk's heartbeat)
mydesk ask status|notify|…      talk to the running MyDesk through its mailbox
mydesk awake --for 120          don't sleep for 2 hours (only on the charger)
mydesk autostart on|off         start at sign-in
mydesk backup | paths | version
```

The downloaded apps include it too: `MyDesk-tool` on Windows/macOS, `mydesk` after the Linux `install.sh`.

## Add your own tool

Copy `mydesk/tools/_template` into your own-tools folder (see the table above) as `<your_tool>/`, edit `tool.json` (name, section, form inputs) and write the script. Restart MyDesk and the tool appears in its section's menu. The full guide is in [CONTRIBUTING.md](CONTRIBUTING.md).

## How it works

```
mydesk/app.py        starts the local server and opens the window (pywebview → Edge WebView2 / WebKit / Qt;
                     falls back to a Chrome/Edge app window)
mydesk/cli.py        the `mydesk` command
mydesk/core/         config, tool discovery, job runner, health, devices, events, mailbox, stay-awake,
                     WhatsApp bridge, HTTP server
mydesk/ui/           the interface (plain HTML, CSS, JavaScript; no build step)
mydesk/tools/<id>/   one folder per tool: tool.json + script
packaging/           PyInstaller recipe, Windows installer, Linux installer
relay/               optional WhatsApp relay (Cloudflare Worker)
```

Component, deployment, state and sequence diagrams are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Run the checks with `python -m unittest discover tests`. GitHub Actions runs them on Windows, macOS and Linux for every push.

## License

[MIT](LICENSE)
