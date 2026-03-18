#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  HTML → APK Builder  |  run_converter.sh
#  Developed by BALAVIGNESH A
# ─────────────────────────────────────────────────────────────

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            HTML → APK Builder                           ║"
echo "║            Developed by BALAVIGNESH  A                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Check Python ───────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Install Python 3.10+ first."
    exit 1
fi

# ── Check input HTML ───────────────────────────────────────────
if [ ! -f "input_project/index.html" ]; then
    echo "[ERROR] Missing: input_project/index.html"
    echo "Please place your HTML file in the input_project/ folder."
    exit 1
fi

# ── Run ────────────────────────────────────────────────────────
python3 converter.py

echo ""
if [ -f "output/app.apk" ]; then
    echo "✅ APK ready → output/app.apk"
    echo "   Install: adb install output/app.apk"
else
    echo "ℹ️  Android project generated → build/android_project/"
    echo "   Open in Android Studio to build the APK."
fi
echo ""
