#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "requirements.txt" || ! -f "app.py" ]]; then
  echo "Error: 请在 backend 目录运行此脚本（当前目录应包含 requirements.txt 与 app.py）" >&2
  echo "Hint: cd backend && ./start.sh" >&2
  exit 1
fi

PYTHON="${PYTHON:-}"
if [[ -z "${PYTHON}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
  else
    echo "Error: 未找到 python3/python，请先安装 Python3（建议命令名为 python3）" >&2
    echo "Hint: 或者手动指定：PYTHON=python3 ./start.sh" >&2
    exit 1
  fi
fi

if [[ ! -f ".venv/Scripts/python.exe" && ! -f ".venv/bin/python" ]]; then
  echo "Creating venv: .venv"
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

PID_FILE="backend.pid"
LOG_FILE="backend.log"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" >/dev/null 2>&1; then
    echo "Backend already running (pid=${old_pid})."
    echo "Log: $(pwd)/${LOG_FILE}"
    exit 0
  fi
fi

echo "Starting backend in background..."
nohup "$VENV_PY" app.py >"$LOG_FILE" 2>&1 &
new_pid="$!"
echo "$new_pid" >"$PID_FILE"

echo "Started. pid=${new_pid}"
echo "Log: $(pwd)/${LOG_FILE}"

