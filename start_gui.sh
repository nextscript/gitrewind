#!/usr/bin/env bash
# Startet GitRewind (GUI) ohne zusätzliches Konsolen-Fenster.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python wurde nicht gefunden. Bitte Python installieren." >&2
  exit 1
fi

if ! "$PY" -c "import PyQt6" >/dev/null 2>&1; then
  echo "PyQt6 wird nicht gefunden. Installieren: pip install PyQt6" >&2
  exit 1
fi

nohup "$PY" git_rewind_gui.py >/dev/null 2>&1 &
echo "GitRewind gestartet (Fenster im Hintergrund)."
