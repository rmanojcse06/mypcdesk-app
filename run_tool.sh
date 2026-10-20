#!/usr/bin/env bash
# Run any MyDesk tool from a terminal:  ./run_tool.sh list   |   ./run_tool.sh clip_saver "<url>"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/mytool.py" "$@"
