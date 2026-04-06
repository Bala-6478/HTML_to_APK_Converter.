@echo off
title HTML to APK Builder - Developed by BALAVIGNESH A
echo ============================================================
echo   HTML to APK Builder  ^|  Developed by BALAVIGNESH A
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

where java >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Java not found. JDK 17 is required for compilation.
    echo           Install from: https://adoptium.net
    echo.
)

python converter.py
echo.
if errorlevel 1 (
    echo Build encountered an error. Check the logs\ folder for details.
) else (
    echo Done! Check output\app.apk
)
pause
