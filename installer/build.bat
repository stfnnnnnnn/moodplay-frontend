@echo off
setlocal enabledelayedexpansion

title MoodPlay Installer — Build

echo.
echo  ============================================================
echo   MoodPlay Installer Builder
echo   Packages installer.py into a single MoodPlayInstaller.exe
echo  ============================================================
echo.

:: ── Prerequisite: Python on PATH ───────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH.
    echo         Install Python 3.11+ and ensure it is added to PATH, then re-run.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [INFO]  Using %%v

:: ── Prerequisite: pip ──────────────────────────────────────────────────────
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not available. Run: python -m ensurepip --upgrade
    pause
    exit /b 1
)

:: ── Install / upgrade build dependencies ──────────────────────────────────
echo.
echo [STEP 1/4]  Installing Python dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause
    exit /b 1
)
echo [OK]    Dependencies installed.

:: ── WebView2 runtime check (advisory only) ────────────────────────────────
echo.
echo [STEP 2/4]  Checking WebView2 runtime...
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" >nul 2>&1
if errorlevel 1 (
    reg query "HKCU\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" >nul 2>&1
)
if errorlevel 1 (
    echo [WARN]  WebView2 runtime NOT detected.
    echo         The built .exe requires WebView2 on the target machine.
    echo         Download: https://developer.microsoft.com/en-us/microsoft-edge/webview2/
    echo         (Build will continue — just note this for distribution.)
) else (
    echo [OK]    WebView2 runtime detected.
)

:: ── Clean previous build artefacts ────────────────────────────────────────
echo.
echo [STEP 3/4]  Cleaning previous build artefacts...
if exist "dist\MoodPlayInstaller.exe" (
    del /f /q "dist\MoodPlayInstaller.exe"
    echo [OK]    Removed old dist\MoodPlayInstaller.exe
)
if exist "build" (
    rmdir /s /q "build"
    echo [OK]    Removed build\ folder
)

:: ── Run PyInstaller ────────────────────────────────────────────────────────
echo.
echo [STEP 4/4]  Running PyInstaller (this may take 1-3 minutes)...
echo.
python -m PyInstaller MoodPlayInstaller.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. See output above for details.
    pause
    exit /b 1
)

:: ── Done ──────────────────────────────────────────────────────────────────
echo.
echo  ============================================================
if exist "dist\MoodPlayInstaller.exe" (
    echo   BUILD SUCCESSFUL
    echo.
    for %%F in ("dist\MoodPlayInstaller.exe") do (
        set /a size_kb=%%~zF/1024
        echo   Output : dist\MoodPlayInstaller.exe
        echo   Size   : !size_kb! KB
    )
    echo.
    echo   Distribute dist\MoodPlayInstaller.exe to the target machine.
    echo   The target machine must have the WebView2 runtime installed.
    echo   The .exe will auto-request Administrator privileges on launch.
) else (
    echo   BUILD FAILED — dist\MoodPlayInstaller.exe not found.
)
echo  ============================================================
echo.
pause
endlocal
