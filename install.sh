#!/usr/bin/env bash
# MyDesk installer for macOS and Linux.
# Creates .venv, installs packages, and opens MyDesk when you log in.
#   ./install.sh               install + start at login
#   ./install.sh --no-startup  install only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STARTUP=1
[[ "${1:-}" == "--no-startup" ]] && STARTUP=0

echo
echo "  MyDesk installer"
echo "  Folder: $ROOT"
echo

PY=""
for c in python3.12 python3.11 python3.13 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" -c 'import sys; print("%d%02d" % sys.version_info[:2])')
    if (( v >= 310 && v <= 313 )); then PY="$c"; break; fi
  fi
done
if [[ -z "$PY" ]]; then
  echo "Python 3.10 - 3.13 not found. Install it (e.g. from python.org or your package manager) and run again."
  exit 1
fi
echo "[1/3] Using $($PY --version)"

[[ -x "$ROOT/.venv/bin/python" ]] || "$PY" -m venv "$ROOT/.venv"
VPY="$ROOT/.venv/bin/python"

echo "[2/3] Installing packages (first time takes a few minutes)"
"$VPY" -m pip install --upgrade pip --quiet
"$VPY" -m pip install -r "$ROOT/requirements.txt" --quiet
if [[ "$(uname)" == "Linux" ]]; then
  # pywebview on Linux needs Qt (or GTK). Without it MyDesk opens in a Chrome/Edge app window instead.
  "$VPY" -m pip install --quiet "pywebview[qt]" || echo "      (Qt window engine not installed; a browser app window will be used)"
fi

echo "[3/3] Shortcuts"
if [[ "$(uname)" == "Darwin" ]]; then
  PLIST="$HOME/Library/LaunchAgents/com.mydesk.app.plist"
  if (( STARTUP )); then
    mkdir -p "$(dirname "$PLIST")"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.mydesk.app</string>
  <key>ProgramArguments</key><array><string>$VPY</string><string>$ROOT/mydesk.py</string></array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>RunAtLoad</key><true/>
</dict></plist>
EOF
    echo "      MyDesk will open when you log in (remove: rm \"$PLIST\")."
  fi
else
  APPS="$HOME/.local/share/applications"
  mkdir -p "$APPS"
  DESKTOP="[Desktop Entry]
Type=Application
Name=MyDesk
Comment=Your personal desktop of tools
Exec=\"$VPY\" \"$ROOT/mydesk.py\"
Path=$ROOT
Icon=$ROOT/ui/mydesk.png
Terminal=false
Categories=Utility;"
  echo "$DESKTOP" > "$APPS/mydesk.desktop"
  if (( STARTUP )); then
    mkdir -p "$HOME/.config/autostart"
    echo "$DESKTOP" > "$HOME/.config/autostart/mydesk.desktop"
    echo "      MyDesk will open when you log in (remove: rm ~/.config/autostart/mydesk.desktop)."
  fi
fi
chmod +x "$ROOT/run_tool.sh" "$ROOT/mydesk.sh" 2>/dev/null || true

echo
echo "Done! Starting MyDesk..."
nohup "$VPY" "$ROOT/mydesk.py" >/dev/null 2>&1 &
