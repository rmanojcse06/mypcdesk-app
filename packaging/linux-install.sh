#!/usr/bin/env bash
# Install the MyDesk Linux build for this user: ~/.local/opt/MyDesk, a `mydesk` command,
# a menu entry, and (unless --no-startup) start at login.  Run from the unpacked folder.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/opt/MyDesk"
mkdir -p "$HOME/.local/opt" "$HOME/.local/bin" "$HOME/.local/share/applications"
rm -rf "$DEST" && cp -r "$SRC" "$DEST"
ln -sf "$DEST/MyDesk-tool" "$HOME/.local/bin/mydesk"
ICON="$(find "$DEST" -name mydesk.png | head -1)"
cat > "$HOME/.local/share/applications/mydesk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=MyDesk
Exec=$DEST/MyDesk
Icon=$ICON
Categories=Utility;
EOF
[[ "${1:-}" == "--no-startup" ]] || "$DEST/MyDesk-tool" autostart on
echo "Installed. Open MyDesk from your app menu, or run: mydesk"
