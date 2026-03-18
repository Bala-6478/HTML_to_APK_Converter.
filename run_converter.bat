@echo off
title HTML to APK Builder — Developed by BALAVIGNESH A
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║            HTML to APK Builder                          ║
echo  ║            Developed by BALAVIGNESH A                   ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

REM ── Check Python ──────────────────────────────────────────────
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

REM ── Check index.html exists ────────────────────────────────────
if not exist "input_project\index.html" (
    echo  [ERROR] No index.html found in input_project\
    echo  Please place your HTML file at:  input_project\index.html
    pause
    exit /b 1
)

REM ── Run the converter ──────────────────────────────────────────
echo  Starting build process...
echo.
python converter.py

echo.
if exist "output\app.apk" (
    echo  ✅ SUCCESS — APK is ready at:  output\app.apk
) else (
    echo  ℹ️  Project generated in build\android_project\
    echo  Open it in Android Studio to complete the build.
)

echo.
pause
