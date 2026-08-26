#!/usr/bin/env bash
# Start GitRewind (GUI) without an additional console window.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python was not found. Please install Python." >&2
  exit 1
fi

if ! "$PY" -c "import PyQt6" >/dev/null 2>&1; then
  echo "PyQt6 was not found. Install with: pip install PyQt6" >&2
  exit 1
fi

nohup "$PY" git_rewind_gui.py >/dev/null 2>&1 &
echo "GitRewind started (window in the background)."
