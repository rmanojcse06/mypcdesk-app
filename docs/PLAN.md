# MyDesk: build, run and ship plan

MyDesk is a personal desktop app for Windows, macOS and Linux. It keeps your own tools in one colourful window, starts at sign-in, and stays running until you end it in Task Manager. This page is the roadmap: what exists, what comes next, and how it gets to other people.

See also: [ARCHITECTURE.md](ARCHITECTURE.md) (diagrams) · [INSTALL.md](INSTALL.md) (install steps) · [CHANGELOG.md](../CHANGELOG.md).

## Where things stand (1.0.0-beta.2, Oct 2026)

| Area | Status |
| --- | --- |
| App shell: window, tray, single copy, start at sign-in, close-to-minimize | Built |
| Health strip: CPU, memory, every drive, USB devices, audio jack, touchscreen, lock keys, plug-in pop-ups | Built |
| OS Monitor with **Ports in use** | Built |
| Tools: **Clip Maker**, **MyCheats** | Built |
| Calendar with per-occurrence acknowledgements; notification bell | Built |
| Dialog counter in the title bar | Built |
| "Is my PC on?" heartbeat, phone use through Claude (file mailbox), stay-awake on charger | Built |
| WhatsApp commands through your own relay | Built, not yet tried with a real Meta account |
| `mydesk` command, pipx package, per-user data folders, `mydesk backup` | Built |
| Release builds (Windows installer, portable zip, macOS app, Linux tarball, wheel) | CI recipe written; first build runs on the first tag push |
| Three-panel **lobby** (Health, Tools, Claude) with tips strip | Designed and prototyped ([`docs/design/`](design/)) |
| Zucker (social manager), TechBite (trends + GitHub activity) | Planned |

## How the app behaves

- Opens at sign-in; one copy only. A second launch brings the running window forward.
- The close button minimizes (or hides to tray with `"close_button": "tray"`). It ends only from Task Manager, or a tray **Quit** if `"tray_quit": true`.
- Health refreshes every 1.5 s; plug-ins and lock keys show within seconds.
- Each tool is its own script, so a stuck tool never freezes the window, and every tool also runs from a terminal (`mydesk run <tool>`).
- Dialogs (MyCheats sheets and future tool windows) are counted in the title bar, e.g. "MyDesk — 2 dialogs open".
- Calendar badge counts unacknowledged events in the next 15 days and earlier this month; it turns red at 3 days or less.

The lobby (designed, next to build) has four states — Default, Health focused, Claude focused, Maximized — with the tips strip always at the top. State diagrams are in [ARCHITECTURE.md §5](ARCHITECTURE.md#5-state-diagrams).

### Remote use from your phone

| Need | How it works | Cost |
| --- | --- | --- |
| Is my computer on? | `status.json` every 30 s; `mydesk status` reads its age: ON, probably asleep, or off | 0 tokens to write; a short Claude message to ask |
| Alert when the PC goes off | Optional `heartbeat_url`: outgoing check-in every 5 min to a monitor that pings your phone when check-ins stop | 0 |
| Use MyDesk remotely via Claude | Claude drops a request in `data/inbox/`; MyDesk runs allow-listed actions and answers in `data/outbox/` | A few thousand tokens per request |
| Use MyDesk from WhatsApp | Meta → your Cloudflare relay → MyDesk polls it (no ports open) | Free tiers |
| Keep the PC awake while Claude works | Held only on the charger, released on battery | 0 |

MyDesk never runs shell commands from the mailbox or WhatsApp — only registered tools — and remote actions pop up on screen.

## Resource needs (MyDesk + lobby)

| Resource | Amount | How we know |
| --- | --- | --- |
| Memory: server (Python) | ~27 MB, flat | Measured |
| Memory: window (WebView2) | 100-170 MB | Estimate |
| Memory: each open dialog | 40-80 MB | Estimate |
| CPU at rest | ~0.4% of one core | Measured |
| CPU, Windows device checks | 2-5% of one core in short spikes every 6 s | Estimate; step 2 replaces polling with plug-in events |
| Network inside the PC | ~0.33 KB/s to 127.0.0.1 | Measured |
| Network to the internet | 0 at rest; only when a tool needs it | Measured |
| Disk: code | 0.4 MB (+ ~3 MB design images) | Measured |
| Disk: Python + core packages | 130-180 MB | Estimate |
| Disk: Clip Maker packages (OCR, yt-dlp, ffmpeg) | 250-350 MB, optional | Estimate |
| Disk: your data | Grows: 5-50 MB per clip with video, ~3 MB without | Estimate |
| Database | None now: JSON + Markdown files | Design |

Move to SQLite (built into Python) when token history for the lobby (~100 B per Claude request, ~3.6 MB/year at 100/day) and full-text search across hundreds of clips arrive.

**Token stats in the lobby** come from Anthropic's [Usage and Cost API](https://platform.claude.com/docs/en/manage-claude/usage-cost-api), which needs an organization **Admin API key** (Claude Console). Poll at most once a minute and cache in SQLite. Fallback for individual accounts: count tokens from MyDesk's own Claude calls.

## Development steps

| Step | What gets built | Done when | Status |
| --- | --- | --- | --- |
| 0. Foundation | Window, server, tool runner, health, OS Monitor + Ports, Clip Maker, MyCheats, calendar, notifications, tests | Smoke tests pass | Done |
| 1. Design | Lobby screens, tips strip, clickable prototype | You approve the prototype | Done, awaiting OK |
| 1b. Remote + packaging | Heartbeat, mailbox, stay-awake, WhatsApp relay, `mydesk` CLI, per-user folders, release CI | beta.1 and beta.2 tagged | Done |
| 2. Light on Windows | Plug-in events instead of 6 s PowerShell scan; JSON → SQLite | Idle CPU < 1%; plug-in shows within 2 s | Next |
| 3. Build the lobby | Three panels, expand, maximize, restore, scroll, favourites strip | Every prototype interaction works in the app | |
| 4. Tips strip | Stored tips, editor, pin, reorder, speed, pause on hover, upcoming events added automatically | Tips survive a restart and scroll smoothly | |
| 5. Claude panel | Streaming chat; token stats cached each minute; budget and projection | Numbers match the Claude Console | |
| 6. New tools | TechBite (AI/ML, cybersecurity, GenAI, Spring/Java trends + your GitHub activity), Zucker (social manager) | Each runs from the lobby and from `mydesk run` | |
| 7. Updates | In-app update check, verify, backup, silent install, migrations, rollback | beta → beta upgrade keeps all data; downgrade opens after one restore | |
| 8. Release 1.0 | Signed installer, README with screenshots, first users | 3 people outside your PC use it for a week | |

How to build each step:

1. **Branch per step**, e.g. `git switch -c lobby`; merge to `main` when its "done when" check passes.
2. **Design, then code.** Change the prototype first when the look changes, then copy the agreed layout into `mydesk/ui/`.
3. **Every tool is a script** in its own folder with a `tool.json` ([CONTRIBUTING.md](../CONTRIBUTING.md)).
4. **Keep tests green:** `python -m unittest discover tests`; CI runs the same on Windows, macOS and Linux.
5. **Use it daily** from your working copy and note anything slow or confusing as a GitHub issue.

## Shipping MyDesk to other people

1. **Bundle** with PyInstaller (one-folder): `MyDesk` + `MyDesk-tool`, no Python needed. Core ~60-90 MB; Clip Maker's OCR is an optional extra.
2. **User data outside the app folder** (`%APPDATA%\MyDesk` etc.), so updates and uninstalls never touch it. Done in beta.2.
3. **Installer:** Inno Setup on Windows (sign-in start option, shortcuts, uninstaller); `.app` on macOS; tarball + `install.sh` on Linux; wheel for pipx. Done in beta.2 CI.
4. **Sign it:** a code-signing certificate (or Microsoft Trusted Signing) removes SmartScreen's "unknown publisher"; Apple Developer account (~$99/yr) for notarizing on macOS.
5. **Publish on GitHub Releases:** pushing a tag like `v1.0.0` builds everything and uploads it with `SHA256SUMS.txt`.
6. **Updates:** once a day MyDesk asks GitHub for the newest release on your channel (Stable or Beta) and offers it; never silently.
7. **Later:** `winget install MyDesk`, Homebrew cask, AppImage/Flatpak.

Before other people use it:

- [ ] Make the GitHub repo public
- [ ] Privacy note in the README: everything stays on the user's PC, no tracking
- [ ] Clip Maker notice: users follow each platform's terms; saved videos are for personal reference
- [ ] Settings screen (name, close button, Claude key) so nobody edits JSON
- [ ] First-run welcome explaining the tray icon and Task Manager behaviour
- [ ] Crash log in the settings folder with a "copy log" button

## Versions, upgrade and downgrade

- `MAJOR.MINOR.PATCH`, with `-beta.N` for test builds. PATCH = fixes; MINOR = new tools/features; MAJOR = data changes you can't skip.
- Two channels: **Stable** (no dash) and **Beta** (also `-beta`).
- Upgrade flow: check → offer → download → verify SHA-256 → back up → install silently → migrate data (`data/schema.json`) → on failure restore the backup and reinstall the previous version. Sequence diagram in [ARCHITECTURE.md §6.9](ARCHITECTURE.md#69-upgrade-planned-for-step-7-mydesk-backup-exists-today).
- Downgrade = install the older version; if it uses an older data format, restore the backup taken just before upgrading. An older version that finds newer data refuses to open it rather than editing it.
- Rules: migrations only add; old fields kept for one MINOR version; installer never touches the data folder; CI tests upgrade and downgrade before each release.

Manual steps today are in [INSTALL.md](INSTALL.md#upgrade).

## Risks and open questions

| Risk | Impact | Plan |
| --- | --- | --- |
| Windows-only parts (tray, device checks, dialogs, stay-awake) not yet run on a real PC | Something may not behave as described | Install on your laptop and report; fix before step 3 |
| First release build untested | Installer may need fixes | Watch the first tag's Actions run and fix the recipe |
| USB scan via PowerShell every 6 s | Small CPU spikes | Step 2: plug-in events |
| Token stats need an Admin API key | Lobby tiles empty on an individual account | Count MyDesk's own calls instead |
| Sites change their pages | Clip Maker downloads break | Update yt-dlp; clear error message |
| Unsigned installer | SmartScreen / Gatekeeper warnings | Sign before the public release |
| Personal data in `data/` | Private birthdays, clips, tips | Never committed; kept in the per-user folder |

Open questions:

- [ ] Is the lobby prototype's layout right, or should anything move before step 3?
- [ ] Do you want a Claude Console organization for the token stats?
- [ ] Which tool first after the lobby: TechBite or Zucker?

## Related idea: social and tech-blog tools

The original tool ideas that MyDesk grew from, to be built as tools in later steps:

- **Clip Maker** (built): save reels/videos from YouTube, Instagram, Facebook, LinkedIn with caption, screenshots and OCR as Markdown.
- **Zucker**: list the accounts and channels you follow or subscribe to across platforms, and manage posting.
- **TechBite**: daily digest of trends in AI/ML, cybersecurity, GenAI and Spring/Java, your GitHub activity, and topics you want to learn; drafts tech-blog posts (backend, AI/ML, CCNA) as Markdown in a GitHub repo and shares them to LinkedIn after you approve.
