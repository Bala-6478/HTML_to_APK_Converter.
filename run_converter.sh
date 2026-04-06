#!/usr/bin/env bash
# ============================================================
#   HTML to APK Builder  |  Developed by BALAVIGNESH A
# ============================================================

set -euo pipefail

echo "============================================================"
echo "  HTML to APK Builder  |  Developed by BALAVIGNESH A"
echo "============================================================"
echo

# ── Check Python ─────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3.10+."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(sys.version_info >= (3,10))")
if [ "$PY_VER" != "True" ]; then
    echo "[WARNING] Python 3.10+ is recommended."
fi

# ── Check Java ────────────────────────────────────────────────
if ! command -v java &>/dev/null; then
    echo "[WARNING] java not found. JDK 17 is required for compilation."
    echo "          Install from: https://adoptium.net"
    echo
fi

# ── Run converter ─────────────────────────────────────────────
python3 converter.py
STATUS=$?

echo
if [ $STATUS -ne 0 ]; then
    echo "Build encountered an error. Check the logs/ folder for details."
    exit $STATUS
else
    echo "Done! Check output/app.apk"
fi
