#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python}"

if [[ ! -f ".venv/Scripts/python.exe" && ! -f ".venv/bin/python" ]]; then
  echo "Creating venv: backend/.venv"
  "$PYTHON" -m venv .venv
fi

if [[ -f ".venv/Scripts/python.exe" ]]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

echo "Installing dependencies..."
"$VENV_PY" -m pip install -U pip
"$VENV_PY" -m pip install -r requirements.txt

echo "Starting backend..."
"$VENV_PY" app.py

