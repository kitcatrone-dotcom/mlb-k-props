#!/usr/bin/env bash
# One-shot setup for AI DJ Edit Studio.
# Safe to re-run; every step is idempotent.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== AI DJ Edit Studio setup ==="

# --- 1. System dependency checks ---
missing=()
command -v ffmpeg >/dev/null 2>&1 || missing+=("ffmpeg")
command -v python3 >/dev/null 2>&1 || missing+=("python3")
command -v node >/dev/null 2>&1 || missing+=("node")
command -v npm >/dev/null 2>&1 || missing+=("npm")
command -v rubberband >/dev/null 2>&1 || missing+=("rubberband-cli")

if [ ${#missing[@]} -ne 0 ]; then
  echo ""
  echo "Missing system dependencies: ${missing[*]}"
  echo ""
  echo "Install them first, then re-run this script:"
  echo "  macOS   : brew install ffmpeg node rubberband"
  echo "  Ubuntu  : sudo apt install ffmpeg nodejs npm rubberband-cli"
  echo "  Windows : winget install ffmpeg; winget install OpenJS.NodeJS.LTS"
  echo "            (rubberband on Windows: install via MSYS2 or use the"
  echo "             librosa fallback noted in README.md)"
  exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
echo "Found python3 $PY_VERSION, node $(node -v), ffmpeg OK, rubberband OK"

# --- 2. Python virtual environment + backend deps ---
echo ""
echo "--- Backend (Python) ---"
cd "$ROOT_DIR/backend"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
deactivate

# --- 3. Node deps (root + frontend) ---
echo ""
echo "--- Frontend (Node) ---"
cd "$ROOT_DIR"
npm install
cd frontend
npm install
cd "$ROOT_DIR"

# --- 4. Pre-fetch Demucs model weights so the first render isn't slow ---
echo ""
echo "--- Pretrained models ---"
cd "$ROOT_DIR/backend"
source .venv/bin/activate
python3 "$ROOT_DIR/scripts/download_models.py"
deactivate

echo ""
echo "=== Setup complete ==="
echo "Run 'npm run dev' from $ROOT_DIR to start the app."
