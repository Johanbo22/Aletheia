#!/usr/bin/env bash
set -e

echo "[INFO] Starting Aletheia build process..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

if ! command -v python3 &> /dev/null; then
  echo "[ERROR] python3 is not installed or not available in system PATH"
  exit 1
fi

echo "[INFO] Creating virtual environment"
python3 -m venv build_env
source build_env/bin/activate

echo "[INFO] Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -e .
python3 -m pip install pyinstaller

echo "[INFO] Compiling the Aletheia binary..."
if [ -f "Aletheia.spec" ]; then
    pyinstaller Aletheia.spec --clean
else
    echo "[ERROR] Aletheia.spec file not found in the root directory."
    exit 1
fi

echo "[INFO] Build complete"
echo "The compiled binary is located in the 'dist' directory."
exit 0