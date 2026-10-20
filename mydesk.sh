#!/usr/bin/env bash
# Open MyDesk (macOS / Linux).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/mydesk.py" "$@"
